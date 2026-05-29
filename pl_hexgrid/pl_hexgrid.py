#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# GIMP plugin for creation of hexagonal grids, with a "best fit" search
# algorithm within a size interval, for optimal rasterization.
#
# Original author : Pascal Lachat
# Version 0.16 for GIMP 3.0 and (probably) later


# License: GPLv3
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY, without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# To view a copy of the GNU General Public License
# visit: http://www.gnu.org/licenses/gpl.html




# Changelog:
# ---------
# 0.16
    # Renamed "quality" parameter to "accuracy".
    # Partial rewrite to allow for non-stretched grids, where center of hexagons don't 
        # land on the pixel grid. Horizontal or vertical faces are still adjusted to the 
        # pixels. This should make the plugin generally more useful for cases where an 
        # exact pixel snap is not required. The "Snap centers to pixels" checkbox controls 
        # this option.
    # Better output text for samples and layers/paths names.
    # UI revamped with better parameters visual hierarchy.
    # Size can now be enter as width, apothem, radius or line spacing
    # Added option to filter by accuracy.
    # Interval of search has been replaced by a single size parameter and the accuracy 
        # filter. If the filter is on, the nearest suitable size(s) is (are) selected.
    # Option to output advanced parameters, like lines and contiguous hexagons count.
        # Displayed parameters depend on the "Snap centers to pixels" option.
    # Samples are now rectangles and make better use of the available space.
    # More consistant borders widths for samples sheets frames.
    # Translated the code comments in english.
# 0.15
    # Internationalization enabled, fr language added
# 0.14
    # layer dimensions and offsets taken into account when drawing on the current layer
    # added basic menu select for color
    # added message in error console when there isn't enough room for one hexagon
    # completed and started to translate some comments
    # started documenting the plugin
# 0.13
    # corrected calculations when there is only one line of hexagons
    # restructuration for samples sheets
    # added squares repartition into rectangle algorithm
    # implemented well distributed samples sheet, and labels
    # added user dialog parameters for samples
    # corrected quality and delta calculation
    # added display of stretch in the X direction (apothem)
# 0.12
    # restructurated in preparation of samples sheet functionality
# 0.11
    # margins now take stroke width into acount
    # removed halfPixelOffset parameter, deduced from stoke width
    # added more descriptive text for some tooltips
# 0.10
    # recreated user dialog and parameters with the new api
# 0.9
    # converted to GIMP 3.0 api
    # changed registration and UI registration names

# To do:
# -----
# Option for physical units (mm) input (and output?)
# Maybe: optical correction for hexagon vertices

#-------------------
import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi
gi.require_version('Gegl', '0.4')
from gi.repository import Gegl
from gi.repository import GObject
from gi.repository import GLib

import os
import sys
import gettext
#-------------------
import math
#-------------------

LOCALE_DIR = os.path.join(os.path.dirname(__file__), "locale")
gettext.bindtextdomain("pl_hexgrid", LOCALE_DIR)
gettext.textdomain("pl_hexgrid")
_ = gettext.gettext

class hexaGrid (Gimp.PlugIn):
    
    ## GimpPlugIn virtual methods ##
    def do_query_procedures(self):
        return [ "pl-hexgrid" ]

    def do_set_i18n(self, name):
        return True
    
    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(self, name,
                                            Gimp.PDBProcType.PLUGIN,
                                            self.run, None)

        procedure.set_image_types("*")
        
        procedure.set_menu_label(_("Hexagonal grid..."))
        procedure.set_icon_name(GimpUi.ICON_GEGL)
        procedure.add_menu_path('<Image>/Filters/Render/Pattern')

        procedure.set_documentation(_("Creates an optimized hexagonal grid as a path. Stroking the path is optional."),
                                    _("Creates an optimized hexagonal grid as a path. Stroking the path is optional."),
                                    name)
        procedure.set_attribution("Pascal L.", "Pascal L.", "2025")

        # Boite de dialogue
        #-------------------
        choice = Gimp.Choice.new()
        choice.add(                     "make hexgrid", 0, _("Hexagonal grid"), "")
        choice.add(                     "make samples", 1, _("Samples sheet"), "")
        procedure.add_choice_argument(  "createSamplesChoice", _("Output"), _("Choose what to draw"),
                                        choice, "make hexgrid", GObject.ParamFlags.READWRITE )
        procedure.add_int_argument(     "sampleCount", _("\t\tSamples count"),
                                        _("Number of samples on the sample sheet"),
                                        1, 25, 12, GObject.ParamFlags.READWRITE )
        choice = Gimp.Choice.new()
        choice.add(                     "width",         0, _("Width"), "")
        choice.add(                     "apothem",       1, _("Apothem"), "")
        choice.add(                     "radius",        2, _("Radius, edge (approx.)"), "")
        choice.add(                     "lines spacing", 3, _("Lines spacing (approx.)"), "") # fr: interligne
        procedure.add_choice_argument(  "sizeChoice", _("Size parameter"), 
                                        _("Choose what the \"Size\" parameter represents. Apothem is half the width"),
                                        choice, "width", GObject.ParamFlags.READWRITE )
        procedure.add_int_argument(     "size", _("\t\tSize (px)"),
                                        _("Hexagon defining size"),
                                        4, 10000, 50, GObject.ParamFlags.READWRITE )
        procedure.add_boolean_argument( "allowStretch", _("Snap centers to pixels"), # fit, coincide, correlate, adjust, pin, snap?
                                        _("Stretch or compress slightly to snap hexagon centers to pixels"), 
                                        False, GObject.ParamFlags.READWRITE )
        procedure.add_boolean_argument( "snapFilterOn", _("\tFilter by accuracy"),
                                        _("Only output grids with sufficient snap accuracy"), 
                                        False, GObject.ParamFlags.READWRITE )
        procedure.add_int_argument(     "threshold", _("\t\tSnap accuracy"),
                                        _("How much snap distortion tolerated, expressed as fraction of 1 pixel"),
                                        2, 1000, 5, GObject.ParamFlags.READWRITE )
        choice = Gimp.Choice.new()
        choice.add(                     "horizontal", 0, _("Horizontal"), "")
        choice.add(                     "vertical",   1, _("Vertical"), "")
        procedure.add_choice_argument(  "orientation", _("Orientation"), _("Orientation"),
                                        choice, "horizontal", GObject.ParamFlags.READWRITE )
        procedure.add_int_argument(     "marginH", _("Vertical margins (px)"),
                                        _("Minimal vertical margins"),
                                        -500, 1000, 0, GObject.ParamFlags.READWRITE )
        procedure.add_int_argument(     "marginV", _("Horizontal margins (px)"),
                                        _("Minimal horizontal margins"),
                                        -500, 1000, 0, GObject.ParamFlags.READWRITE )
        procedure.add_boolean_argument( "createLayer", _("Create a new layer"),
                                        _("Create a new layer - always active for samples sheet"), 
                                        True, GObject.ParamFlags.READWRITE )
        procedure.add_boolean_argument( "strokePath", _("Stroke the path"),
                                        _("Stroke the path - always active for samples sheet"), 
                                        True, GObject.ParamFlags.READWRITE )
        procedure.add_int_argument(     "strokeWidth", _("\tStroke width (px)"),
                                        _("Stroke width. If odd, the path will be offset by a half-pixel"),
                                        1, 50, 2, GObject.ParamFlags.READWRITE )
        choice = Gimp.Choice.new()
        choice.add(                     "foreground", 0, _("Foreground color"), "")
        choice.add(                     "black",      1, _("Black"), "")
        procedure.add_choice_argument(  "selectedColor", _("\tStroke color:"), _("Color"),
                                        choice, "black", GObject.ParamFlags.READWRITE )
        procedure.add_boolean_argument( "keepPaths", _("Keep the path"),
                                        _("Keep the path (hexagonal grid only)"), 
                                        False, GObject.ParamFlags.READWRITE )
        procedure.add_boolean_argument( "adjustGrid", _("Adjust image grid"),
                                        _("Adjust the image grid to coincide with the center of hexagons (hexagonal grid only)"), 
                                        False, GObject.ParamFlags.READWRITE )
        procedure.add_boolean_argument( "verbose", _("Output advanced parameters"),
                                        _("Output more parameters in layers name and sample text"), 
                                        False, GObject.ParamFlags.READWRITE )


        return procedure


    def run(self, procedure, run_mode, monImage, drawables, config, run_data):
        
        #----------------
        # main procedure
        #----------------
        
        # All calculation are done with virtual X and Y axes, where those axes are switched 
        # when hexas direction is set to "vertical". Original, unswitched parameters are 
        # generally postfixed with H and V.
        
        
        # dialog -----------------------------------------------------------------
        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init('pl_hexgrid') # file name

            dialog = GimpUi.ProcedureDialog(procedure=procedure, config=config)
            dialog.fill(None)
            if not dialog.run():
                dialog.destroy()
                return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())
            else:
                dialog.destroy()
        
        createSamplesChoice = config.get_property('createSamplesChoice')
        sampleCount         = config.get_property('sampleCount')
        size                = config.get_property('size')
        sizeChoice          = config.get_property('sizeChoice')
        allowStretch        = config.get_property('allowStretch')
        snapFilterOn        = config.get_property('snapFilterOn')
        threshold           = config.get_property('threshold')
        orientation         = config.get_property('orientation')
        marginH             = config.get_property('marginH')
        marginV             = config.get_property('marginV')
        createLayer         = config.get_property('createLayer')
        strokePath          = config.get_property('strokePath')
        strokeWidth         = config.get_property('strokeWidth')
        selectedColor       = config.get_property('selectedColor')
        keepPaths           = config.get_property('keepPaths')
        adjustGrid          = config.get_property('adjustGrid')
        verbose             = config.get_property('verbose')
        
        
        #-----------------------------------------------------------------------------
        
        # dev variables---------------------------------------------------------------
        
        cropLayer           = False   # unused
        createSampleImage   = False   # create another image? unused
        
        #-----------------------------------------------------------------------------
        
        # get active layer------------------------------------------------------------
        
        if len(drawables) != 1:
            msg = _("Procedure '{}' only works with one drawable.").format(procedure.get_name())
            error = GLib.Error.new_literal(Gimp.PlugIn.error_quark(), msg, 0)
            return procedure.new_return_values(Gimp.PDBStatusType.CALLING_ERROR, error)
        else:
                calqueSource = drawables[0]
        
        #-----------------------------------------------------------------------------
        
        # Initialisations-------------------------------------------------------------
        
        if createLayer == True or createSamplesChoice == "make samples" :
            # for some reason, we can't freeze layers if working on the source layer, and make it selected
            monImage.freeze_layers()
            monImage.freeze_paths()
        
        Gimp.context_push()
        fgColor = Gimp.context_get_foreground()
        Gimp.context_set_defaults()
        
        monImage.undo_group_start()
        
        #-----------------------------------------------------------------------------
        
        trueRatio = math.sqrt(3.0)
        
        if createSamplesChoice == "make hexgrid" :
            createSampleSheet = False
            sampleCount = 1
        else :
            createSampleSheet = True
            
        match sizeChoice : 
            case "width" :
                targetApothem = math.ceil(size / 2.0)
            case "apothem" :
                targetApothem = size
            case "radius" :
                targetApothem = round( 3 * size / (2 * trueRatio) )
            case "lines spacing" :
                targetApothem = round(size / trueRatio)
        
        if selectedColor == "black" :
            fgColor = Gimp.color_parse_name("black") 
        
        
        if snapFilterOn == False :
            threshold = 2
        
        threshold = 1.0 / threshold  # threshold of difference in separation from perfect grid
        
        marginH += strokeWidth // 2  # division with floor
        marginV += strokeWidth // 2
        
        if orientation == 'horizontal' :
            direction = 'horizontal' #???
            marginX = marginH
            marginY = marginV

        else :
            direction = 'vertical'
            marginX = marginV
            marginY = marginH
                
        # end if
        
        # check stroke width parity---------------------------------------------------
        
        if strokeWidth % 2 == 1 :
                
                halfPixel = 0.5
        else :
                halfPixel = 0.0
        
        
        # end initialisations
        #-----------------------------------------------------------------------------
        
        # Search magic numbers--------------------------------------------------------
        
        # print("Sample count:", sampleCount) # debug
        
        if allowStretch == True :
            
            sampleList = sampleSearchThres(targetApothem, threshold, sampleCount, trueRatio)
            
        else :
            
            sampleList = sampleSearchInterv(targetApothem, sampleCount, trueRatio)
            
        # print(sampleList) # debug

        #-----------------------------------------------------------------------------
        
        # Creation phase initialisations----------------------------------------------
        
        if createLayer == False and createSampleSheet == False :
                
                imageH = calqueSource.get_width()
                imageV = calqueSource.get_height()
                baseLayerOffset = calqueSource.get_offsets() # exception: the first element is the boolean!!
                baseLayerOffsetH = baseLayerOffset[1]
                baseLayerOffsetV = baseLayerOffset[2]
                
        else :
                imageH = monImage.get_width()
                imageV = monImage.get_height()
                baseLayerOffsetH = 0
                baseLayerOffsetV = 0
        
        if direction == 'horizontal' :
                
                imageX = imageH
                imageY = imageV
                baseLayerOffsetX = baseLayerOffsetH
                baseLayerOffsetY = baseLayerOffsetV
                
        else :
                
                imageX = imageV
                imageY = imageH
                baseLayerOffsetX = baseLayerOffsetV
                baseLayerOffsetY = baseLayerOffsetH
                
        # end if
        
        # print(baseLayerOffsetX) # debug
        # print(baseLayerOffsetY) # debug
        
        #-----------------------------------------------------------------------------
        
        # Creation phase--------------------------------------------------------------
        
        
        if createSampleSheet == True :
            
            Gimp.Selection.none(monImage)
            createLayer = True
            adjustGrid = False
            strokePath = True
            keepPaths = False
            marginX = strokeWidth // 2
            marginY = strokeWidth // 2
            
            # prepare grid dimensions
            gridLineWidth = strokeWidth + 2 #(strokeWidth // 2) * 2 + 2 # ensure it's even
            gridLineOffset = 0 # -1 * (gridLineWidth // 2)
            
            layerGroup = Gimp.GroupLayer.new(monImage, "Samples sheet #1") # add more details to the name?
            monImage.insert_layer(layerGroup, None, 0)
            
            # determine best filling of squares :
            cellSize, nrows, ncols = squareFill(imageH - gridLineWidth, imageV - gridLineWidth, sampleCount)
            
            # stretch the squares for better fill
            cellSizeH, cellSizeV = stretchSquares(imageH - gridLineWidth, imageV - gridLineWidth, cellSize, nrows, ncols)
            
            if direction == 'horizontal' :
                cellSizeX = cellSizeH
                cellSizeY = cellSizeV
            else :
                cellSizeX = cellSizeV
                cellSizeY = cellSizeH
            
            # insert background white layer
            bgroundH = cellSizeH * ncols + gridLineWidth
            bgroundV = cellSizeV * nrows + gridLineWidth
            # bgLayer = Gimp.Layer.new(   monImage, None, cellSizeH * ncols, cellSizeV * nrows, 
                                        # 1, 100.0, Gimp.LayerMode.NORMAL)
            bgLayer = Gimp.Layer.new(   monImage, None, bgroundH, bgroundV, 
                                        1, 100.0, Gimp.LayerMode.NORMAL)
            monImage.insert_layer(bgLayer, layerGroup, 1)
            bgLayer.fill(3)   # white
            
            i = 0
            
            for thisElement in sampleList :
                
                # suggestion for congruence:    snap: accuracy (fidélité), convergence, evenness, symmetry, divergence, uniformity, pixel-shift
                #                               non-snap: congruence, convergence, accordance, divergence, tolerance, pixel-shift (lines)
                apothem =       thisElement["apothem"]
                radius =        thisElement["radius"]
                separation =    thisElement["separation"]
                congruence =    thisElement["congruence"] 
                gridStretch =   thisElement["gridStretch"]
                delta =         thisElement["delta"]
                
                offsetX = (i % ncols) * cellSizeH + gridLineWidth // 2
                offsetY = (i // ncols ) * cellSizeV + gridLineWidth // 2
                
                buildHexagons(  monImage, calqueSource, cellSizeX, cellSizeY, baseLayerOffsetX, baseLayerOffsetY, 
                                offsetX, offsetY, marginX, marginY, direction, apothem, radius, 
                                separation, allowStretch, halfPixel, congruence, delta, gridStretch, 
                                createLayer, strokePath, strokeWidth, fgColor, adjustGrid, 
                                layerGroup, True, keepPaths, verbose)
                
                i += 1
                
            # end for
            
            # merge group
            sampleLayer = layerGroup.merge()
            
            # decorate with grid
            grid = Gimp.DrawableFilter.new(sampleLayer, "gegl:grid", "")
            grid_config = grid.get_config()
            grid_config.set_property("x", cellSizeH)
            grid_config.set_property("y", cellSizeV)
            grid_config.set_property("x-offset", gridLineOffset)
            grid_config.set_property("y-offset", gridLineOffset)
            grid_config.set_property("line-width", gridLineWidth)
            grid_config.set_property("line-height", gridLineWidth)
            grid_config.set_property("line-color", Gegl.Color.new('black'))
            sampleLayer.merge_filter(grid)
            
            # center the samples layer
            layerPushH = (imageH - bgroundH) // 2
            layerPushV = (imageV - bgroundV) // 2
            sampleLayer.set_offsets(layerPushH, layerPushV)
            
            # flatten and extend to image size
            backgroundcolor = Gimp.color_parse_css("rgb(255, 255, 255)")
            Gimp.context_set_background(backgroundcolor)
            sampleLayer.flatten()
            sampleLayer.resize_to_image_size()
            
        else : # createSampleSheet == False
            
            layerGroup = None
            
            thisElement = sampleList[0]
            offsetX = 0
            offsetY = 0
            
            apothem =       thisElement["apothem"]
            radius =        thisElement["radius"]
            separation =    thisElement["separation"]
            congruence =    thisElement["congruence"]
            gridStretch =   thisElement["gridStretch"]
            delta =  thisElement["delta"]
            
            buildHexagons(  monImage, calqueSource, imageX, imageY, baseLayerOffsetX, baseLayerOffsetY, 
                            offsetX, offsetY, marginX, marginY, direction, apothem, radius, 
                            separation, allowStretch, halfPixel, congruence, delta, gridStretch, 
                            createLayer, strokePath, strokeWidth, fgColor, adjustGrid, 
                            layerGroup, False, keepPaths, verbose)
            
        # end if createSampleSheet
        
        #-----------------------------------------------------------------------------
        
        #----------------------
        # End of main procedure
        #----------------------
        
        # print(selectedLayer[0]) # debug
        
        monImage.undo_group_end()
        
        Gimp.context_pop()
        
        # make current layer active
        
        monImage.set_selected_layers([calqueSource])
        
        if createLayer == True :
            
            monImage.thaw_paths()
            monImage.thaw_layers()
            selectedLayer = monImage.get_layers()[0]
            # monImage.set_selected_layers([calqueSource])    # bug workaround : without this line, and in 
                                                              # presence of freeze/thaw, no layer is selected!
            monImage.set_selected_layers([selectedLayer])
            
            
        
        
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())
        
#*************************************************************************************


def stretchSquares(imageH, imageV, cellSize, nrows, ncols) :
    
    # determine in which direction we can stetch
    extentH = cellSize * ncols
    extentV = cellSize * nrows
    pixLeftH = imageH - extentH
    pixLeftV = imageV - extentV
    
    if pixLeftH > pixLeftV and pixLeftH > ncols : # we can add some pixels horizontally
        
        addedPixH = pixLeftH // ncols
        cellSizeH = cellSize + addedPixH
        cellSizeV = cellSize
        
    elif pixLeftV > pixLeftH and pixLeftV > nrows : # we can add some pixels vertically
        
        addedPixV = pixLeftV // nrows
        cellSizeV = cellSize + addedPixV
        cellSizeH = cellSize
        
    else :
        
        cellSizeH = cellSize
        cellSizeV = cellSize
    
    return cellSizeH, cellSizeV


#*************************************************************************************


def sampleSearchInterv(targetApothem, sampleCount, trueRatio) :

    # used if allowStretch is false

    # Initialisations-----------------------------------------------------------------
    
    minApothem = 2
    
    lowerApothem = max(minApothem, targetApothem - int(sampleCount / 2.0))
    upperApothem = lowerApothem + sampleCount - 1
    currentApothem = lowerApothem
    sampleList = []
    
    # calculate all the deltas--------------------------------------------------------
    
    while currentApothem <= upperApothem : 
        
        separation = currentApothem * trueRatio # separation between hexas lines, height of the grid rectangle
        delta = abs(round(separation) - separation)
        gridStretch = 0.0 #
        
        # congruence :
        congruence = 1.0 / delta

        radius = separation / 3.0 * 2.0
        
        sampleList.append( {"apothem":currentApothem, "delta":delta, 
                            "delta":delta,
                            "separation":separation, "radius":radius,
                            "congruence":congruence, "gridStretch":gridStretch} )
        
        currentApothem +=1
    
    # end while
    
    # print(sampleList) # debug
    
    #---------------------------------------------------------------------------------
    
    return sampleList
    
#*************************************************************************************

def sampleSearchThres(targetApothem, threshold, sampleCount, trueRatio) :
    
    # -------------------------------------------
    # search of multiple samples of magic numbers
    # -------------------------------------------
    
    # used if allowStretch is true
    
    # Initialisations-----------------------------------------------------------------
    
    minApothem = 2
    inc = 0.5           # increment to add and subtract alternatively to target Apothem
    toggle = 1         # alternatively 1 and -1
    sampleList = []
    
    # calculate all the deltas--------------------------------------------------------
    
    while sampleCount > 0 : 
        
        currentApothem = targetApothem + toggle * int(inc)
        
        trueSeparation = currentApothem * trueRatio
        
        separation = round(trueSeparation) # separation between hexas lines, height of the grid rectangle
        delta = separation - trueSeparation
        
        if abs(delta) <= threshold and currentApothem >= minApothem :
            
            if sampleCount == 1 and toggle == -1 and threshold < 0.5 :  # if last pass is lower apothem
                
                # we examine the symetric higer apothem to see if it's better
                currentApothem1 = targetApothem + int(inc)
                trueSeparation1 = currentApothem1 * trueRatio
                separation1 = round(trueSeparation1)
                delta1 = separation1 - trueSeparation1
                
                if abs(delta1) < abs(delta) :
                    
                    currentApothem = currentApothem1
                    trueSeparation = trueSeparation1
                    separation = separation1
                    delta = delta1
            
            # end if sampleCount...
            
            # congruence :
            congruence = 1.0 / abs(delta) # number of contiguous hexs to deviate 1px, changed since 0.16
            radius = separation / 3.0 * 2.0
            gridStretch = trueSeparation / separation #
            
            sampleList.append( {"apothem":currentApothem, "delta":delta, 
                                "delta":delta,
                                "separation":separation, "radius":radius,
                                "congruence":congruence, "gridStretch":gridStretch} )
            sampleCount -= 1
            
        # end if abs(delta)...
        
        inc += 0.5
        toggle *= -1
        
    # end while
    
    # sort full list------------------------------------------------------------------
    
    sampleList.sort(key=byApothem)
    
    # print(sampleList) # debug
    
    #-----------------------------------------------------------------------------
    
    return sampleList

    
#*************************************************************************************


def byDelta(e) : # currently unused
    return e["delta"]
    

#*************************************************************************************

    
def byApothem(e) :
    return e["apothem"]
    

#*************************************************************************************


def squareFill(x, y, n) : # from stackexchange question 466198
    
    # Find biggests n squares that fit into the image
    
    # Compute number of rows and columns, and cell size
    ratio = x / y
    ncolsFloat = math.sqrt(n * ratio)
    nrowsFloat = n / ncolsFloat
    
    # Find best option filling the whole height
    nrows1 = math.ceil(nrowsFloat)
    ncols1 = math.ceil(n / nrows1)
    
    while (nrows1 * ratio) < ncols1 :
        nrows1 += 1
        ncols1 = math.ceil(n / nrows1)
        
    cellSize1 = y / nrows1
    
    # Find best option filling the whole width
    ncols2 = math.ceil(ncolsFloat)
    nrows2 = math.ceil(n / ncols2)
    
    while ncols2 < (nrows2 * ratio) :
        ncols2 += 1
        nrows2 = math.ceil(n / ncols2)
        
    cellSize2 = x / ncols2
    
    # Find the best values
    if cellSize1 <= cellSize2 : # changed from "<" to favor horizontal #noideawhyitworks
        nrows = nrows2
        ncols = ncols2
        cellSize = cellSize2
    else :
        nrows = nrows1
        ncols = ncols1
        cellSize = cellSize1
    
    return int(cellSize), nrows, ncols


#*************************************************************************************


def countHexagons( dimX, dimY, marginX, marginY, apothem, separation ):

    # count contiguous hexas and lines
    
    countY = int( (dimY - 2.0 * marginY - 1.0 / 3.0 * separation) / separation )
    
    if countY > 1 :  # add an apothem to take into account the offset of even lines
        countX = int( (dimX - 2.0 * marginX - apothem) / (2.0 * apothem) )
        
    else : # countY == 1 or 0
        countX = int( (dimX - 2.0 * marginX) / (2.0 * apothem) )
        
    # end if
    
    return countX, countY


#*************************************************************************************


def buildHexagons(  monImage, calqueSource, dimX, dimY, baseLayerOffsetX, baseLayerOffsetY, 
                    offsetH, offsetV, marginX, marginY, direction, apothem, radius, 
                    separation, allowStretch, halfPixel, congruence, delta, gridStretch, 
                    createLayer, strokePath, strokeWidth, fgColor, adjustGrid, 
                    layerGroup, isSample, keepPaths, verbose):
    
    # This function could use some restructuring...
    
    # ***************************************
    # Hexagons counting, building and drawing
    # ***************************************
    
    #---------------------------------------------------------------------------------
    
    # initialisations-----------------------------------------------------------------
    
    offsetX = offsetH
    offsetY = offsetV
    
    if isSample == True :
        pageMarginX = marginX
        pageMarginY = marginY
        marginX -= int(apothem * 1.5) # à vérifier
        marginY -= int(apothem * 1.5)
    
    countX, countY = countHexagons(dimX, dimY, marginX, marginY, apothem, separation)
    
    if countX == 0 or countY == 0 :
        Gimp.message_set_handler(2)
        Gimp.message("Impossible to draw a " + str(2 * apothem) + 
                    "px wide hexagon.\nTry with a smaller range or a bigger image")
        return(False)
    
    # print("count:" + str(countX) + "x" + str(countY)) # debug
    
    # title of path and layer---------------------------------------------------------
    
    if allowStretch == True :
        
        dgridStretch = (1.0 - gridStretch) * 100   # delta of stretch for grid height direction, in %
        rndStretch = 0 - int(math.floor(math.log10(abs(dgridStretch)))) # decimal places minus 1
        
        if dgridStretch < 0 :
            dStretchSign = "-"
        else :
            dStretchSign = "+"
            
        rndDelta = 1 - int(math.floor(math.log10(abs(delta)))) # decimal places minus 1
        
        if direction == 'horizontal' :
            
            gridXY = str( int(apothem) ) + "x" + str( int(separation) )
            countXY = str(countX) + "x" + str(countY)
            
        else :
            
            gridXY = str( int(separation) ) + "x" + str( int(apothem) ) 
            countXY = str(countY) + "x" + str(countX)
        
        if verbose :
            vectorName = (
                    _("W:") + str( int(apothem * 2) ) +
                    _(" grid:") + gridXY +
                    _(" accur:") + str( int(round(congruence)) ) +
                    _(" str:") + dStretchSign + str( round(abs(dgridStretch), rndStretch) ) + "%" +
                    # _(" snap:") + str( round(delta, rndDelta) ) +
                    _(" count:") + countXY
                    )
        else :
            vectorName = (
                    _("W:") + str( int(apothem * 2) ) +
                    _(" grid:") + gridXY +
                    _(" accur:") + str( int(round(congruence)) )
                    )
            
    else : # allowStretch == False
        
        delta = 0.0
        rndStretch = 2
        dgridStretch = 0.0
        dStretchSign = ""
        
        if direction == 'horizontal' :
            
            gridXY = str( int(apothem) ) + "x" + str( round(separation, 2) )
            countXY = str(countX) + "x" + str(countY)
            
        else :
            
            gridXY = str( round(separation, 2) ) + "x" + str( int(apothem) )
            countXY = str(countY) + "x" + str(countX)
            
        if verbose :
            
            vectorName = (
                    _("W:") + str( int(apothem * 2) ) +
                    _(" grid:") + gridXY +
                    _(" radius:") + str( round(radius, 1) ) +
                    _(" count:") + countXY
                    )
        else :
            vectorName = (
                    _("W:") + str( int(apothem * 2) ) +
                    _(" grid:") + gridXY
                    )
    
    # end if allowStretch
    
    layerName = vectorName
    
    
    #---------------------------------------------------------------------------------
    
    # Create a new layer
    # ---------------
    
    if createLayer == True :
        
        newLayerX = dimX
        newLayerY = dimY
        
        layerOffsetX = math.floor( (dimX - newLayerX) / 2.0 + halfPixel )
        layerOffsetY = math.floor( (dimY - newLayerY) / 2.0 + halfPixel )
        
        layerType = calqueSource.type_with_alpha()
        
        if direction == 'horizontal' :
            
            newLayer = Gimp.Layer.new(  monImage, layerName, newLayerX, newLayerY, 
                                        layerType, 100, Gimp.LayerMode.NORMAL)
            newLayer.set_offsets(layerOffsetX + offsetH, layerOffsetY + offsetV)
            # offsetH, offsetV: samples offsets
            
        else :
            newLayer = Gimp.Layer.new(  monImage, layerName, newLayerY, newLayerX, 
                                        layerType, 100, Gimp.LayerMode.NORMAL)
            newLayer.set_offsets(layerOffsetY + offsetH, layerOffsetX + offsetV)
            # offsetH, offsetV: samples offsets
        
        # end if
        
        monImage.insert_layer(newLayer, layerGroup, 0)
        
        # selectedLayer = newLayer
        
    # else : 
            
        # selectedLayer = calqueSource
            
    # end if createLayer
    
    #---------------------------------------------------------------------------------
    
    # Construction
    # ------------
    
    # offsets : coordinates of the first hexagon center
    
    if isSample == True and direction == 'vertical' :
        offsetX = offsetV
        offsetY = offsetH
    
    totalOffsetX = baseLayerOffsetX
    totalOffsetY = baseLayerOffsetY
    
    if isSample == True :
        totalOffsetX += offsetX
        totalOffsetY += offsetY
        
    pathOffsetX = 0.5 * dimX - apothem * countX + totalOffsetX
    pathOffsetY = 0.5 * ( dimY - separation * (countY - 1) ) + totalOffsetY
    
    if countY > 1 or isSample == True : # take even lines offset into account
        pathOffsetX -= 0.5 * apothem
    
    pathOffsetX = math.floor(pathOffsetX) + halfPixel
    
    if allowStretch == True :
        pathOffsetY = math.floor(pathOffsetY)
    
    pathOffsetY += halfPixel
    
    # vectors from center to vertices
    
    if direction == 'horizontal' :
            
            vectA = [0.0, -radius]
            vectB = [apothem, -radius/2.0]
            vectC = [apothem, radius/2.0]
            vectD = [0.0, radius]
            vectE = [-apothem, radius/2.0]
            vectF = [-apothem, -radius/2.0]
            
    else :
            
            vectA = [-radius, 0.0]
            vectB = [-radius/2.0, apothem]
            vectC = [radius/2.0, apothem]
            vectD = [radius, 0.0]
            vectE = [radius/2.0, -apothem]
            vectF = [-radius/2.0, -apothem]
    
    # end if
    
    # empty path creation
    
    hexgrid = Gimp.Path.new(monImage, vectorName)
    
    
    # Build iteration-----------------------------------------------------------------
    
    i = 0
    while i < countY :
            
            centerV = i * separation + pathOffsetY
            lineParity = i % 2
            startX = apothem * (lineParity + 1.0)
            
            j = 0
            while j < countX :
                    
                    centerH = 2.0 * apothem * j + startX + pathOffsetX
                    
                    
                    if direction == 'horizontal' :
                            
                            centerX = centerH
                            centerY = centerV
                            
                    else :
                            
                            centerX = centerV
                            centerY = centerH
                            
                    
                    # on dessine un hexagone
                    hexgrid.stroke_new_from_points(0, [
                            centerX + vectA[0],
                            centerY + vectA[1],
                            centerX + vectA[0],
                            centerY + vectA[1],
                            centerX + vectA[0],
                            centerY + vectA[1],
                            centerX + vectB[0],
                            centerY + vectB[1],
                            centerX + vectB[0],
                            centerY + vectB[1],
                            centerX + vectB[0],
                            centerY + vectB[1],
                            centerX + vectC[0],
                            centerY + vectC[1],
                            centerX + vectC[0],
                            centerY + vectC[1],
                            centerX + vectC[0],
                            centerY + vectC[1],
                            centerX + vectD[0],
                            centerY + vectD[1],
                            centerX + vectD[0],
                            centerY + vectD[1],
                            centerX + vectD[0],
                            centerY + vectD[1],
                            centerX + vectE[0],
                            centerY + vectE[1],
                            centerX + vectE[0],
                            centerY + vectE[1],
                            centerX + vectE[0],
                            centerY + vectE[1],
                            centerX + vectF[0],
                            centerY + vectF[1],
                            centerX + vectF[0],
                            centerY + vectF[1],
                            centerX + vectF[0],
                            centerY + vectF[1]
                            ], True)
                    
                    j += 1
            
            i += 1
    
    #---------------------------------------------------------------------------------
    
    #---------------
    # Finalisations
    #---------------
    
    # important: only insert the path when it's complete
    
    monImage.insert_path(hexgrid, None, 0)
    
    
    # stroke the path-----------------------------------------------------------------
    
    if strokePath == True :
            
            Gimp.context_set_foreground(fgColor)
            Gimp.context_set_line_width(strokeWidth)
            Gimp.context_set_antialias(True)
            Gimp.context_set_line_join_style(0) #MITER
            Gimp.context_set_stroke_method(0)   #LINE
            
            if createLayer == True :
                    newLayer.edit_stroke_item(hexgrid)
            else :
                    calqueSource.edit_stroke_item(hexgrid)
            
    else :
            
            hexgrid.set_visible(True)
    
    # remove path if wanted
    
    if keepPaths == False :
        
        monImage.remove_path(hexgrid)
    
    # set the image grid---------------------------------------------------------------
    
    if adjustGrid == True :
            
            monImage.grid_set_style(1) # INTERSECTIONS
            
            if direction == 'horizontal' :
                    
                    monImage.grid_set_spacing(apothem, separation)
                    monImage.grid_set_offset(pathOffsetX, pathOffsetY)
                    
            else :
                    
                    monImage.grid_set_spacing(separation, apothem)
                    monImage.grid_set_offset(pathOffsetY, pathOffsetX)
                    
            # end if
            
            # display image grid: currently not possible with the API?
            # would be useful for user choice confirmation
            
    # end if
    
    # info-text layer-----------------------------------------------------------------
    
    if isSample == True :
        
        imageH = monImage.get_width()
        imageV = monImage.get_height()
        
        if direction == 'horizontal' :
            
            dirStretch = _("v stretch:")
            totalCountH, totalCountV = countHexagons(imageH, imageV, 
                                                    pageMarginX, pageMarginY, apothem, separation)
            
        else : 
            
            dirStretch = _("h stretch:")
            totalCountV, totalCountH = countHexagons(imageV, imageH, 
                                                    pageMarginY, pageMarginX, apothem, separation)
            
        # end if direction
        
        sampleText = _(" width/apo: ") + str( int(2 * apothem) ) + "/" + str( int(apothem) ) + "px"
        
        if allowStretch == True :
            
            if verbose :
                
                sampleText = ( sampleText + "\n" +
                            _(" spacing  : ") + str( int(separation) ) + "px\n" +
                            " " + dirStretch + dStretchSign + str( round(abs(dgridStretch), rndStretch) ) + "%\n" +
                            # _(" snap dist: ") + str( round(abs(delta), rndDelta ) ) + "px\n" +
                            _(" accuracy : ") + str( round(congruence, 1) ) + "\n" +
                            _(" count    : ") + str(totalCountH) + "x" + str(totalCountV)
                            )
                
            else : # not verbose
                
                sampleText = ( sampleText + "\n" +
                            _(" spacing  : ") + str( int(separation) ) + "px\n" +
                            _(" accuracy : ") + str( round(congruence, 1) ) 
                            )
        
        else : # allowStretch == False
            
            if verbose :
                
                sampleText = ( sampleText + "\n" +
                            _(" spacing  : ") + str( round(separation, 2) ) + "px\n" +
                            _(" radius   : ") + str( round(radius, 1) ) + "px" + "\n" +
                            _(" count    : ") + str(totalCountH) + "x" + str(totalCountV)
                            )
                            
            else : # not verbose
                
                sampleText = ( sampleText + "\n" +
                            _(" spacing  : ") + str( round(separation, 2) ) + "px"
                            )
        
        # end if allowStretch
        
        # configure the text layer
        fontScale = 20.0         # relative scaling # default: 20
        refDim = min(dimX, dimY) # take the smallest side as reference for font scaling
        fontSize = fontScale * refDim / 500.0 + 6.0 # unit px
        textOffsetX = offsetH + int(0.5 * math.sqrt(refDim)) + strokeWidth
        textOffsetY = offsetV + int(0.5 * math.sqrt(refDim)) + strokeWidth
        font = Gimp.Font.get_by_name("Monospace Bold")
        unit = Gimp.Unit.pixel()
        textColor       = Gimp.color_parse_css("rgb(0, 0, 0)")
        backgroundcolor = Gimp.color_parse_css("rgb(250, 250, 225)")
        
        # create the text layer
        newTextLayer = Gimp.TextLayer.new(monImage, sampleText, font, fontSize, unit)
        newTextLayer.set_offsets(textOffsetX, textOffsetY)
        monImage.insert_layer(newTextLayer, layerGroup, 0)
        newTextLayer.set_color(textColor)
        
        x = newTextLayer.get_width()
        y = newTextLayer.get_height()
        textFrame = Gimp.Layer.new(monImage, None, x, y, 1, 100.0, Gimp.LayerMode.NORMAL)
        textFrame.set_offsets(textOffsetX, textOffsetY)
        monImage.insert_layer(textFrame, layerGroup, 1)
        Gimp.context_set_background(backgroundcolor)
        textFrame.fill(1)
        
    # end if isSample
    
    return
    
# end buildHexagons()

#*************************************************************************************


Gimp.main(hexaGrid.__gtype__, sys.argv)



