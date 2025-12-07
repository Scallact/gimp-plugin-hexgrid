#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# GIMP plugin for creation of hexagonal grids, with a "best fit" search
# algorithm within a size interval, for optimal rasterization.
#
# Original author : Pascal Lachat
# Version 0.15 for GIMP 3.0 and (probably) later


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


"""

Hexagonal grid
**************

This GIMP plugin aims to draw regular hexagonal grids that fit the pixel grid as perfectly 
as possible, avoiding some common artefact like blurred vertical or horizontal lines. This 
optimisation also ensures that each hexagon is exactly the same and symmetrical.

As no perfect fit exists between a square grid (pixels) and an hexagonal one, hexagons' 
proportions are slightly stretched. The amount of deformation depends on their size. 
The working size factor of the plugin is the apothem, i.e. the distance between the 
center and the middle of a face. The user interface presents a more understandable 
"width" parameter, a measure of the distance between two faces.

Please note that the hexagons "width" can be horizontal or vertical, depending on the 
orientation selected.


Parameters :

- The plugin comes with a search function for the best fit in a given size interval, 
  selected by "quality" (see below). To choose a specific width, simply enter "0" in the
  "Maximal hexagon width" field.
- Choose "Sample sheet" at the "Output" drop-down menu to create a sheet with multiple 
  grid samples, selected by quality, in a nice tabular format. Width, quality and 
  stretch (%) are displayed on each sample.
- The "quality" output parameter explicits the number of contiguous hexagons that reach 
  a mis-alignment of one pixel between the actual and ideal grids.
- If "Create a new layer" or "Keep the path" are checked, the name of the layer and/or 
  path will display the hexagon width, quality, and the size of the corresponding image 
  grid (width x height).
- The image grid can be automatically set by the plugin. 
- When an odd "Stroke width" is entered, the plugin will shift the hexagonal and image 
  grids by half a pixel for best stroke quality.
- To extend the hexagonal grid past the layer's boundaries, simply enter negative margins. 


Some future improvements are planned:

  - Allow finer granularity at the half-pixel level for the search of the best grid.
   This will relax the Y axis symmetry constraint, without significant loss of 
   visual quality.
  - Optical correction at nodes, where 3 edges meet. Very much needed for large 
   stroke width, but the illusion is there at all scales and the edges must
   subtly become thicker near the node to appear correct to the eye.


About the code:
    
The variable naming scheme is a bit confusing right now and needs revision, 
and the logic is not very well thought out. For instance, it didn't occur to me that 
global variables indeed do exist in Python (!), which use would certainly alleviate 
the growing list of variables passed to some functions.

Some comments are still in french, translation and uniformisation are not completed 
yet. Speaking of translation, I don't know how to localize the plugin, that might 
be a nice thing to do in the future.

"""

# Changelog:
# ---------
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
# Choix couleur >> OK, basic
# Examiner le cas avec aucun hexagone possible (hexagonal grid) >> OK
# Tenir compte des dimensions du calque actuel (seulement pour traçage sur le calque lui-même) >> OK
# Limites samples count pour image < 280 * 280 (16) et < 220 * 220 (9) >> pas nécessaire >> KO
# Permettre une granularité plus fine, au demi-pixel, pour la recherche de séparation, avec option utilisateur


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
        choice1 = Gimp.Choice.new()
        choice1.add(                    "make hexgrid", 0, _("Hexagonal grid"), "")
        choice1.add(                    "make samples", 1, _("Samples sheet"), "")
        procedure.add_choice_argument(  "createSamplesChoice", _("Output"), _("Choose what to draw"),
                                        choice1, "make hexgrid", GObject.ParamFlags.READWRITE)
        procedure.add_int_argument(     "sampleCount", _("Samples count (for samples sheet)"),
                                        _("Number of samples on the sample sheet"),
                                        1, 25, 6, GObject.ParamFlags.READWRITE)
        choice2 = Gimp.Choice.new()
        choice2.add(                    "horizontal", 0, _("Horizontal"), "")
        choice2.add(                    "vertical", 1, _("Vertical"), "")
        procedure.add_choice_argument(  "orientation", _("Orientation"), _("Orientation"),
                                        choice2, "horizontal", GObject.ParamFlags.READWRITE)
        procedure.add_int_argument(     "lowerWidth", _("Minimal hexagon width (px)"),
                                        _("Lower bound of search range for best quality"),
                                        4, 10000, 30, GObject.ParamFlags.READWRITE)
        procedure.add_int_argument(     "upperWidth", _("Maximal hexagon width (px)"),
                                        _("Upper bound, set to 0 for specific width"),
                                        0, 10000, 90, GObject.ParamFlags.READWRITE)
        procedure.add_int_argument(     "strokeWidth", _("Stroke width (px)"),
                                        _("Stroke width. If uneven, the path will be offset by half a pixel"),
                                        1, 50, 2, GObject.ParamFlags.READWRITE)
        procedure.add_int_argument(     "marginXprime", _("Vertical margins (px)"),
                                        _("Minimal vertical margins"),
                                        -500, 1000, 0, GObject.ParamFlags.READWRITE)
        procedure.add_int_argument(     "marginYprime", _("Horizontal margins (px)"),
                                        _("Minimal horizontal margins"),
                                        -500, 1000, 0, GObject.ParamFlags.READWRITE)
        procedure.add_boolean_argument( "createLayer", _("Create a new layer"),
                                        _("Create a new layer - always active for samples sheet"), True, GObject.ParamFlags.READWRITE)
        procedure.add_boolean_argument( "strokePath", _("Stroke the path"),
                                        _("Stroke the path - always active for samples sheet"), True, GObject.ParamFlags.READWRITE)
        choice3 = Gimp.Choice.new()
        choice3.add(                    "foreground", 0, _("Foreground color"), "")
        choice3.add(                    "black", 1, _("Black"), "")
        procedure.add_choice_argument(  "selectedColor", _("Color"), _("Color"),
                                        choice3, "black", GObject.ParamFlags.READWRITE)
        procedure.add_boolean_argument( "keepPaths", _("Keep the path (hexagonal grid)"),
                                        _("Keep the path (hexagonal grid)"), False, GObject.ParamFlags.READWRITE)
        procedure.add_boolean_argument( "adjustGrid", _("Adjust image grid (hexagonal grid)"),
                                        _("Adjust the image grid to coincide with the center of hexagons"), 
                                        False, GObject.ParamFlags.READWRITE)


        return procedure


    def run(self, procedure, run_mode, monImage, drawables, config, run_data):
        
        #----------------
        # main procedure
        #----------------
        
        # All calculation are done with virtual X and Y axes, where those axes are switched 
        # when hexas direction is set to "vertical". Original, unswitched parameters are 
        # sometimes postfixed with "prime" when further use is needed.
        
        
        # boite de dialogue-----------------------------------------------------------
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
        orientation         = config.get_property('orientation')
        lowerWidth          = config.get_property('lowerWidth')
        upperWidth          = config.get_property('upperWidth')
        strokeWidth         = config.get_property('strokeWidth')
        marginXprime        = config.get_property('marginXprime')
        marginYprime        = config.get_property('marginYprime')
        createLayer         = config.get_property('createLayer')
        strokePath          = config.get_property('strokePath')
        selectedColor       = config.get_property('selectedColor')
        keepPaths           = config.get_property('keepPaths')
        adjustGrid          = config.get_property('adjustGrid')
        
        #-----------------------------------------------------------------------------
        
        # dev variables---------------------------------------------------------------
        
        createHexagons = True       # si False, afficher boite de dialogue?
        cropLayer = False
        createSampleImage = False   # créer une autre image ? inutilisé
        
        
        #-----------------------------------------------------------------------------
        
        # récupération calque actif---------------------------------------------------
        
        if len(drawables) != 1:
            msg = _("Procedure '{}' only works with one drawable.").format(procedure.get_name())
            error = GLib.Error.new_literal(Gimp.PlugIn.error_quark(), msg, 0)
            return procedure.new_return_values(Gimp.PDBStatusType.CALLING_ERROR, error)
        else:
                calqueSource = drawables[0]
        
        #-----------------------------------------------------------------------------
        
        # Initialisations-------------------------------------------------------------
        
        Gimp.context_push()
        fgColor = Gimp.context_get_foreground()
        Gimp.context_set_defaults()
        monImage.freeze_layers()
        monImage.freeze_paths()
        
        #-----------------------------------------------------------------------------
        
        if createSamplesChoice == "make hexgrid" :
                createSampleSheet = False
        else :
                createSampleSheet = True
        
        if selectedColor == "black" :
            fgColor = Gimp.color_parse_name("black") 
        
        if createHexagons == True :
                monImage.undo_group_start()
        
        trueRatio = math.sqrt(3.0)
        
        marginXprime += strokeWidth // 2  # division with floor
        marginYprime += strokeWidth // 2
        
        if orientation == 'horizontal' :
                direction = 'horizontal'
                marginX = marginXprime
                marginY = marginYprime

        else :
                direction = 'vertical'
                marginX = marginYprime
                marginY = marginXprime
                
        # end if
        
        # upperWidth and lowerWidth checked and set to conform values-----------------
        
        lowerWidth = math.ceil(lowerWidth / 2.0) * 2.0
        upperWidth = math.floor(upperWidth / 2.0) * 2.0
        
        if upperWidth == 0 :
                upperWidth = lowerWidth
        
        if upperWidth < lowerWidth :

                exchangeBuffer = upperWidth
                upperWidth = lowerWidth
                lowerWidth = exchangeBuffer
                
        # print(lowerWidth) # debug
        # print(upperWidth) # debug
        
        # correct sampleCount if it exceeds the number of possible apothem values-----
        
        sampleCount = min( (upperWidth - lowerWidth) / 2 + 1, sampleCount )
        
        # check stroke width parity---------------------------------------------------
        
        if strokeWidth % 2 == 1 :
                
                halfPixel = 0.5
        else :
                halfPixel = 0.0
        
        
        # end initialisations
        #-----------------------------------------------------------------------------
        
        # Recherche nombres magiques--------------------------------------------------
        
        sampleList = sampleSearch(lowerWidth, upperWidth, trueRatio)
        

        #-----------------------------------------------------------------------------
        
        # Initialisations phase création----------------------------------------------
        
        if createLayer == False and createSampleSheet == False :
                
                imageXprime = calqueSource.get_width()
                imageYprime = calqueSource.get_height()
                baseLayerOffset = calqueSource.get_offsets() # exception: the first element is the boolean!!
                baseLayerOffsetXprime = baseLayerOffset[1]
                baseLayerOffsetYprime = baseLayerOffset[2]
                
        else :
                imageXprime = monImage.get_width()
                imageYprime = monImage.get_height()
                baseLayerOffsetXprime = 0
                baseLayerOffsetYprime = 0
        
        if direction == 'horizontal' :
                
                imageX = imageXprime
                imageY = imageYprime
                baseLayerOffsetX = baseLayerOffsetXprime
                baseLayerOffsetY = baseLayerOffsetYprime
                
        else :
                
                imageX = imageYprime
                imageY = imageXprime
                baseLayerOffsetX = baseLayerOffsetYprime
                baseLayerOffsetY = baseLayerOffsetXprime
                
        # end if
        
        # print(baseLayerOffsetX) # debug
        # print(baseLayerOffsetY) # debug
        
        #-----------------------------------------------------------------------------
        
        # phase création--------------------------------------------------------------
        
        
        curatedSampleList = []
        
        if createSampleSheet == True :
            
            # print("yes") # debug
            
            Gimp.Selection.none(monImage)
            createLayer = True
            adjustGrid = False
            strokePath = True
            keepPaths = False
            marginX = strokeWidth // 2
            marginY = strokeWidth // 2
            
            layerGroup = Gimp.GroupLayer.new(monImage, "Samples sheet #1") # ajouter plus de détails au nom?
            monImage.insert_layer(layerGroup, None, 0)
            
            # determine best filling of squares :
            cellSize, nrows, ncols = squareFill(imageXprime, imageYprime, sampleCount)
            
            # insert background white layer
            bgLayer = Gimp.Layer.new(   monImage, None, cellSize * ncols, cellSize * nrows, 
                                        1, 100.0, Gimp.LayerMode.NORMAL)
            monImage.insert_layer(bgLayer, layerGroup, 1)
            bgLayer.fill(3)   # white
            
            # iterate over samples
            i = 0
            
            while i < sampleCount :
                
                curatedSampleList.append(sampleList[i])
                
                i += 1
                
            curatedSampleList.sort(key=byApothem)
            
            # end while
            
            i = 0
            
            for thisElement in curatedSampleList :
                
                apothem =       thisElement["apothem"]
                radius =        thisElement["radius"]
                separation =    thisElement["separation"]
                quality =       thisElement["quality"]
                apoStretch =    thisElement["apoStretch"]
                
                offsetX = (i % ncols) * cellSize
                offsetY = (i // ncols ) * cellSize
                
                buildHexagons(  monImage, calqueSource, cellSize, cellSize, baseLayerOffsetX, baseLayerOffsetY, 
                                offsetX, offsetY, marginX, marginY, direction, apothem, radius, separation, 
                                halfPixel, quality, apoStretch, createLayer, cropLayer, strokePath, 
                                strokeWidth, fgColor, adjustGrid, layerGroup, True, keepPaths)
                
                i += 1
                
            # end for
            
            # merge group
            sampleLayer = layerGroup.merge()
            
            # decorate with grid
            
            grid = Gimp.DrawableFilter.new(sampleLayer, "gegl:grid", "")
            grid_config = grid.get_config()
            grid_config.set_property("x", cellSize)
            grid_config.set_property("y", cellSize)
            grid_config.set_property("x-offset", -strokeWidth)
            grid_config.set_property("y-offset", -strokeWidth)
            grid_config.set_property("line-width", 2 * strokeWidth)
            grid_config.set_property("line-height", 2 * strokeWidth)
            grid_config.set_property("line-color", Gegl.Color.new('black'))
            sampleLayer.merge_filter(grid)
            
            
            
        else :
            
            layerGroup = None
            
            # curatedSampleList.append(sampleList[0]) # pas nécessaire
            
            thisElement = sampleList[0]
            offsetX = 0
            offsetY = 0
            
            apothem =       thisElement["apothem"]
            radius =        thisElement["radius"]
            separation =    thisElement["separation"]
            quality =       thisElement["quality"]
            apoStretch =    thisElement["apoStretch"]
            
            buildHexagons(  monImage, calqueSource, imageX, imageY, baseLayerOffsetX, baseLayerOffsetY, 
                            offsetX, offsetY, marginX, marginY, direction, apothem, radius, separation, 
                            halfPixel, quality, apoStretch, createLayer, cropLayer, strokePath, 
                            strokeWidth, fgColor, adjustGrid, layerGroup, False, keepPaths)
            
        # end if createSampleSheet
        
        
        #-----------------------------------------------------------------------------
        
        #----------------------
        # End of main procedure
        #----------------------

        monImage.thaw_layers()
        monImage.thaw_paths()
        monImage.undo_group_end() # à faire: tester si undo possible
        Gimp.context_pop()
        
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())
        
#*************************************************************************************


def sampleSearch(lowerWidth, upperWidth, trueRatio) :

    # -------------------------------------------
    # search of multiple samples of magic numbers
    # -------------------------------------------
    
    # Initialisations-------------------------------------------------------------
    
    lowerApothem = int((lowerWidth + 1) / 2.0)
    upperApothem = int(upperWidth / 2.0)
    currentApothem = lowerApothem
    sampleList = []
    
    # boucle de calcul de tous les delta------------------------------------------
    
    while currentApothem <= upperApothem : 
        
        trueSeparation = currentApothem * trueRatio
        separation = round(trueSeparation) # Séparation entre lignes d'hexas. Hauteur du rectangle de grille
        apoStretch = trueSeparation / separation # trick: it's the inverse of stretch in separation (Y) direction!
        delta = abs( 2 * currentApothem * (apoStretch - 1.0) ) # OK, verified graphically
        radius = separation / 3.0 * 2.0
        
        # quality :
        quality = 1.0 / delta # number of contiguous hexs to deviate 1px
        
        sampleList.append( {"apothem":currentApothem, "delta":delta, 
                            "separation":separation, "radius":radius,
                            "quality":quality, "apoStretch":apoStretch} )
        
        # print(quality)    # debug
        # print(apoStretch) # debug
        # print(delta)      # debug
        
        currentApothem +=1
    
    # end while
    
    # tri de la liste complète----------------------------------------------------
    
    sampleList.sort(key=byDelta)
    
    # print(sampleList) # debug
    
    #-----------------------------------------------------------------------------
    
    return sampleList
    
#*************************************************************************************


def byDelta(e) :
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


def buildHexagons(  monImage, calqueSource, dimX, dimY, baseLayerOffsetX, baseLayerOffsetY, 
                    offsetXprime, offsetYprime, marginX, marginY, direction, apothem, radius, 
                    separation, halfPixel, quality, apoStretch, createLayer, cropLayer, strokePath, 
                    strokeWidth, fgColor, adjustGrid, layerGroup, isSample, keepPaths):
    
    # This function has become a monster, restructuring ahead...
    
    # ***************************************
    # Hexagons counting, building and drawing
    # ***************************************
    
    #---------------------------------------------------------------------------------
    
    # initialisations-----------------------------------------------------------------
    
    # fontScale = 1.0       # voir plus bas
    offsetX = offsetXprime
    offsetY = offsetYprime
    
    if isSample == True :
        marginX -= int(apothem * 1.5)
        marginY -= int(apothem * 1.5)
    
    
    # décompte des hexas contigus et des lignes---------------------------------------
    
    countY = int( (dimY - 2.0 * marginY - 1.0 / 3.0 * separation) / separation )
    
    if countY > 1 :  # ajouter un apothem pour tenir compte du décalage des lignes paires
        countX = int( (dimX - 2.0 * marginX - apothem) / (2.0 * apothem) )
        
    else : # countY == 1 or 0
        countX = int( (dimX - 2.0 * marginX) / (2.0 * apothem) )
        
    # end if
    
    if countX == 0 or countY == 0 :
        Gimp.message_set_handler(2)
        Gimp.message("Impossible to draw a " + str(2 * apothem) + 
                    "px wide hexagon.\nTry with a smaller range or a bigger image")
        return(False)
    
    # print(str(countX) + "\n" + str(countY)) # debug
    
    
    # title of path and layer---------------------------------------------------------
    
    dApoStretch = (apoStretch - 1.0) * 100   # delta of stretch for apothem direction, in %
    rndStretch = 0 - int(math.floor(math.log10(abs(dApoStretch)))) # chiffres significatifs (-1)
    
    if dApoStretch < 0 :
        dApoSign = "-"
    else :
        dApoSign = "+"
    
    if direction == 'horizontal' :
            
            vectorName = (
                    _("Wdth:") + str( int(2 * apothem) ) +
                    _(" Qual:") + str( int(round(quality)) ) +
                    "/" + dApoSign + str( round(abs(dApoStretch), rndStretch) ) + "%" +
                    _(" Grid:") + str( int(apothem) ) + "x" + str( int(separation) ) 
                    # " R:" + str( int(round(radius)) ) # removed
                    )
                    
    else :
            
            vectorName = (
                    _("Wdth:") + str( int(2 * apothem) ) +
                    _(" Qual:") + str( int(round(quality)) ) +
                    "/" + dApoSign + str( round(abs(dApoStretch), rndStretch) ) + "%" +
                    _(" Grid:") + str( int(separation) ) + "x" + str( int(apothem) ) 
                    # " R:" + str( int(round(radius)) ) # removed
                    )
    
    # end if
    
    layerName = vectorName
    
    
    #---------------------------------------------------------------------------------
    
    # Créer un calque
    # ---------------
    
    if createLayer == True :
            
            if countY == 1 and isSample == False and cropLayer == True :
                newLayerX = int( 2 * countX * apothem + 2 * marginX + 2 * halfPixel)
                newLayerY = (countY - 1) * separation + 2 * round(2.0 / 3.0 * separation) + 2 * marginY + 2 * halfPixel
                
            elif countY > 1 and isSample == False and cropLayer == True : # tenir compte du décalage des lignes paires
                newLayerX = int( (2 * countX + 1) * apothem + 2 * marginX + 2 * halfPixel)
                newLayerY = (countY - 1) * separation + 2 * round(2.0 / 3.0 * separation) + 2 * marginY + 2 * halfPixel
            
            else : # isSample == True or cropLayer == False
                newLayerX = dimX
                newLayerY = dimY
            
            # end if
            
            layerOffsetX = math.floor( (dimX - newLayerX) / 2.0 + halfPixel )
            layerOffsetY = math.floor( (dimY - newLayerY) / 2.0 + halfPixel )
            
            layerType = calqueSource.type_with_alpha()
            
            if direction == 'horizontal' :
                    
                    newLayer = Gimp.Layer.new(  monImage, layerName, newLayerX, newLayerY, 
                                                layerType, 100, Gimp.LayerMode.NORMAL)
                    newLayer.set_offsets(layerOffsetX + offsetXprime, layerOffsetY + offsetYprime)
                    # offsetXprime, offsetYprime: samples offsets
                    
            else :
                    newLayer = Gimp.Layer.new(  monImage, layerName, newLayerY, newLayerX, 
                                                layerType, 100, Gimp.LayerMode.NORMAL)
                    newLayer.set_offsets(layerOffsetY + offsetXprime, layerOffsetX + offsetYprime)
                    # offsetXprime, offsetYprime: samples offsets
            
            # end if
            
            monImage.insert_layer(newLayer, layerGroup, 0)
            
    # end if createLayer
    
    #---------------------------------------------------------------------------------
    
    # Construction
    # ------------
    
    # offsets : coordonnées du premier centre d'hexagone
    
    if isSample == True and direction == 'vertical' :
        offsetX = offsetYprime
        offsetY = offsetXprime
    
    if countY == 1 and isSample == False :
        pathOffsetX = ( math.floor( ( dimX - apothem * countX * 2 ) / 2.0 ) 
                        + halfPixel + baseLayerOffsetX )
        pathOffsetY = ( math.floor( ( dimY - separation * (countY - 1) ) / 2.0 ) 
                        + halfPixel + baseLayerOffsetY )
        
    elif countY > 1 and isSample == False : # tenir compte du décalage des lignes paires
        pathOffsetX = ( math.floor( ( dimX - apothem * (countX * 2 + 1) ) / 2.0 ) 
                        + halfPixel + baseLayerOffsetX )
        pathOffsetY = ( math.floor( ( dimY - separation * (countY - 1) ) / 2.0 ) 
                        + halfPixel + baseLayerOffsetY )
    
    else : 
        pathOffsetX = ( math.floor( ( dimX - apothem * (countX * 2 + 1) ) / 2.0 ) 
                        + halfPixel + offsetX + baseLayerOffsetX )
        pathOffsetY = ( math.floor( ( dimY - separation * (countY - 1) ) / 2.0 ) 
                        + halfPixel + offsetY + baseLayerOffsetY )

    # vecteurs de position des sommets depuis le centre
    
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
    
    # création du vecteur vide
    
    hexgrid = Gimp.Path.new(monImage, vectorName)
    
    
    # Itération dessin----------------------------------------------------------------
    
    i = 0
    while i < countY :
            
            centerYprime = i * separation + pathOffsetY
            lineParity = i % 2
            startX = apothem * (lineParity + 1.0)
            
            j = 0
            while j < countX :
                    
                    centerXprime = 2.0 * apothem * j + startX + pathOffsetX
                    
                    
                    if direction == 'horizontal' :
                            
                            centerX = centerXprime
                            centerY = centerYprime
                            
                    else :
                            
                            centerX = centerYprime
                            centerY = centerXprime
                            
                    
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
    
    # important: insérer le vecteur seulement lorsqu'il est complet!!!
    
    monImage.insert_path(hexgrid, None, 0)
    
    
    # dessiner les chemin-------------------------------------------------------------
    
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
    
    # adapter la grille---------------------------------------------------------------
    
    if adjustGrid == True :
            
            monImage.grid_set_style(1) # INTERSECTIONS
            
            if direction == 'horizontal' :
                    
                    monImage.grid_set_spacing(apothem, separation)
                    monImage.grid_set_offset(pathOffsetX, pathOffsetY)
                    
            else :
                    
                    monImage.grid_set_spacing(separation, apothem)
                    monImage.grid_set_offset(pathOffsetY, pathOffsetX)
                    
            # end if
            
            # display image grid: apparently not possible with the API
            # would be useful to confirm user choice
            
    # end if
    
    # info-text layer-----------------------------------------------------------------
    
    if isSample == True :
            
        sampleText = (
                    _("width  :") + str( int(2 * apothem) ) + "\n" +
                    _("stretch:") + dApoSign + str( round(abs(dApoStretch), rndStretch) ) + "%\n" +
                    _("quality:") + str( int(round(quality)) ) 
                    )
        
        # configure text layer
        fontScale = 24.0 # relative scaling
        fontSize = fontScale * dimX / 500.0 + 6.0 # unit px
        textOffsetX = offsetXprime + int(0.5 * math.sqrt(dimX)) + strokeWidth
        textOffsetY = offsetYprime + int(0.5 * math.sqrt(dimX)) + strokeWidth
        font = Gimp.Font.get_by_name("Monospace Bold")
        unit = Gimp.Unit.pixel()
        textColor = Gimp.color_parse_css("rgb(0, 89, 188)")
        
        # text layer
        newTextLayer = Gimp.TextLayer.new(monImage, sampleText, font, fontSize, unit)
        newTextLayer.set_offsets(textOffsetX, textOffsetY)
        monImage.insert_layer(newTextLayer, layerGroup, 0)
        newTextLayer.set_color(textColor)
        
        x = newTextLayer.get_width()
        y = newTextLayer.get_height()
        textFrame = Gimp.Layer.new(monImage, None, x, y, 1, 65.0, Gimp.LayerMode.NORMAL)
        textFrame.set_offsets(textOffsetX, textOffsetY)
        monImage.insert_layer(textFrame, layerGroup, 1)
        textFrame.fill(3)
        
    # end if isSample
    
# end buildHexagons()

#*************************************************************************************


Gimp.main(hexaGrid.__gtype__, sys.argv)
