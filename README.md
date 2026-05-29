
# Hexagonal grid for GIMP 3
***************************

This GIMP plugin draws high quality hexagonal grids that fit the pixel grid as perfectly 
as possible, avoiding some common artefact like blurred vertical or horizontal lines. 

Furthermore, the "Snap" option allows to adjust the hexagons centers to the pixel grid.
As no perfect fit exists between a square grid (pixels) and an hexagonal one, hexagons' 
proportions are slightly stretched when this option is active. 

## Plugin dialog

figure_01

## Parameters :

* **Output**
    * Hexagonal grid: main purpose of the plugin, fill a layer with an hexagonal grid.
    * Sample sheet: Create an image sized layer, filled with small rectangular grid samples, 
      each with its descriptive parameters. Useful for comparing and chosing the right size or precision
      for your purpose.
* **Samples count**: how many samples to create, with incremental dimensions distributed around 
  the "Size" parameter. 
* **Size parameter**: Which dimension is used to build hexagons. See fig. 3.
    * Width: distance between two edges. 
    * Apothem: shortest distance from the center to an edge. Half the width.
    * Radius, edge: the radius of the circumscribed circle, which is also the size of an edge.
    * Line spacing: the distance between rows or columns of adjacent hexagons. Along with the apothem, 
      sets the dimensions of the underlying grid.

## Installation:

Extract the .zip file and place the **pl_hexgrid folder** inside your user profile's Plug-ins 
folder. If your OS is Linux or Mac, set the pl_hexgrid.py file executable.

You can find the plugin entry at **Filters > Render > Pattern > Hexagonal grid ...**

## Some future improvements are planned:

  - Allow finer granularity at the half-pixel level for the search of the best grid.
   This will relax the Y axis symmetry constraint, without significant loss of 
   visual quality.
  - Optical correction at nodes, where 3 edges meet. Very much needed for large 
   stroke width, but the illusion is there at all scales and the edges must
   subtly become thicker near the node to appear correct to the eye.

## Translations

The plugin's dialog translations are enabled. Currently only english (by default) and french are available. If you want to contribute to translations in other languages, you're welcome to open a ticket, and attach the .po file if possible.
