
# Hexagonal grid for GIMP 3
***************************

This GIMP plugin draws high quality hexagonal grids that fit the pixel grid as perfectly 
as possible, avoiding some common artefact like blurred vertical or horizontal lines. 

Furthermore, the "Snap" option allows to adjust the hexagons centers to the pixel grid.
As no perfect fit exists between a square grid (pixels) and an hexagonal one, hexagons' 
proportions are slightly stretched when this option is active. 

## Plugin dialog

figure_01

## Parameters

### Output:

* Hexagonal grid: main purpose of the plugin, fill a layer with an hexagonal grid.
* Sample sheet: Create an image sized layer, filled with small rectangular grid samples, 
   each with its descriptive parameters. Useful for comparing and chosing the right size or precision
   for your purpose.
   
### Samples count: 

How many samples to create, with incremental dimensions distributed around 
the "Size" parameter. 

### **Size parameter**:

Which dimension is used to build hexagons. See fig. 3.

* Width: distance between two edges. 
* Apothem: shortest distance from the center to an edge. Half the width.
* Radius, edge: the radius of the circumscribed circle, which is also the size of an edge.
* Line spacing: the distance between rows or columns of adjacent hexagons. Along with the apothem, 
  sets the dimensions of the underlying grid.

### Size

Set dimension for the chosen size parameter. For sample sheets, sets the middle of the interval, or the start
for the search of bigger and smaller sizes.

### Snap centers to pixels:

Slightly stretches the grid to ensure that the hexagons centers fit align exactly with the pixel grid. 
The stretch applies vertically for horizontal grids and horizontally for vertical grids. This is useful 
in many cases, for example if you need to align some stamps perfectly, if you want to draw geometric 
diagrams without the headaches of inter-pixels alignments, or to get nice symetrical hexagons in pixel art.

*Notes*:

* If an odd stroke width is entered, the centers snap at the middle of pixels. If it's even, 
  they snap at the pixels corners.
* Snap "on" was the default and only possible behaviour of previous versions, up to 0.15.
* This option doesn't guarantee that all *vertices* snap to the pixels.

### Filter by accuracy:

*Only for "Snap to center"*

Starting with the "Size" input, searches for the closest size which matches the condition
defined by the "Snap accuracy" parameter.

Especially useful with sample sheet, where the search above and below the target "Size" value
only outputs the results which match the condition.

### Snap accuracy:

*Linked to the option above*
*Only for "Snap to center"*

The **accuracy** qualifies how precisely the stretched grid and the ideal grid spacing
align together. The largest the "accuracy", the less difference between both and the better 
the fit.

It is measured as the fraction of one pixel. For instance, if the grid spacing correction 
between two contiguous lines is 0.2 pixel, the accuracy value is 5 ( 1/0.2 = 5 ).

*Note:* The "Accuracy" equivalent parameter was named "Quality" in previous versions (up to 0.15)

### Orientation:

Direction of contiguous hexagon lines. **Horizontal** or **vertical**.

### Vertical and horizontal margins:

Minimal spacing between the grid and the layer's borders. Accepts negative values, which allow 
to fill the layer fully with partial hexagons at the edge.

*Note:* Unused for sample sheet.

### Create a new layer:

* Uchecked: draws on the active layer, channel or mask. The layer's dimensions are taken into account, 
  which offers another way to enforce margins.
* Checked: creates a new image sized layer.

*Note:* Sample sheet always create a new layer.

### Stroke the path:

Draw the hexagonal grid on the layer. Unchecked, allows to output the path without stroking it, or even 
create a new layer empty named with the parameters values.

### Stroke width:

Self explanatory.

*Note:* If an odd number is entered, the whole grid is displaced by half a pixel to avoid rasterization blur.

### Stroke color:

*Foreground color* or *Black*

*Note:* the foreground color can still be selected while the plugin's dialog is open.

### Keep the path:

*Irrelevant with sample sheet*

Keep the path if needed for further use, like stroke option not provided by the plugin.

### Adjust image grid:

*Irrelevant with sample sheet*

Configure the image grid to fit the centers of hexagons, and highlight the underlying rectangular grid. 
The user still has to activate grid visibility and snap options in GIMP's menus.

### Output advanced parameters

Outputs a few more parameters in layers name (if "Create a new layer" is checked), or in sample sheet 
overlay text. See "Outputs" below for more details.

## Outputs


## Installation:

Extract the .zip file and place the **pl_hexgrid folder** inside your user profile's Plug-ins 
folder. If your OS is Linux or Mac, set the pl_hexgrid.py file executable.

You can find the plugin entry at **Filters > Render > Pattern > Hexagonal grid ...**

## Translations

Translations are enabled. Currently, english (by default), german and french are 
available. If you want to contribute to translations in other languages, you're welcome to open a ticket, 
and attach the .po file if possible.
