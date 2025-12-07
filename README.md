
# Hexagonal grid for GIMP 3
***************************

This GIMP plugin aims to draw regular hexagonal grids that fit the pixel grid as perfectly 
as possible, avoiding some common artefact like blurred vertical or horizontal lines. This 
optimisation also ensures that each hexagon is exactly the same and symmetrical.

As no perfect fit exists between a square grid (pixels) and an hexagonal one, hexagons' 
proportions are slightly stretched. The amount of deformation depends on their size. 
The working size factor of the plugin is the apothem, i.e. the distance between the 
center and the middle of a face. The user interface presents a more understandable 
"**width**" parameter, a measure of the distance between two faces.

Please note that the hexagons "width" can be horizontal or vertical, depending on the 
orientation selected.

## Output

### Sample grid with quality indicators
<img width="660" height="660" alt="Sample_grid_20_to_60" src="https://github.com/user-attachments/assets/2d6516ec-5b7a-44c6-b665-4bddcdd328fa" />

### Hexagonal grid
<img width="660" height="440" alt="Hexagonal_grid_30" src="https://github.com/user-attachments/assets/a4f219a1-3e7f-4815-8afe-8ccf094a937d" />

## Installation:

Extract the .zip file and place the **pl_hexgrid folder** inside your user profile's Plug-ins 
folder. If your OS is Linux or Mac, set the pl_hexgrid.py file executable.

You can find the plugin entry at **Filters > Render > Pattern > Hexagonal grid ...**


## Parameters :

- The plugin comes with a search function for the best fit in a given size interval, 
  selected by "*quality*" (see below). To choose a specific width, simply enter "0" in the
  "Maximal hexagon width" field.
- Choose "**Sample sheet**" at the "Output" drop-down menu to create a sheet with multiple 
  grid samples, selected by quality, in a nice tabular format. Width, quality and 
  stretch (%) are displayed on each sample.
- The "*quality*" output parameter explicits the number of contiguous hexagons that reach 
  a mis-alignment of one pixel between the actual and ideal grids.
- If "**Create a new layer**" or "**Keep the path**" are checked, the name of the layer and/or 
  path will display the hexagon width, quality, and the size of the corresponding image 
  grid (width x height).
- The image grid can be automatically set by the plugin. 
- When an odd "**Stroke width**" is entered, the plugin will shift the hexagonal and image 
  grids by half a pixel for best stroke quality.
- To extend the hexagonal grid past the layer's boundaries, simply enter negative **margins**. 


## Some future improvements are planned:

  - Allow finer granularity at the half-pixel level for the search of the best grid.
   This will relax the Y axis symmetry constraint, without significant loss of 
   visual quality.
  - Optical correction at nodes, where 3 edges meet. Very much needed for large 
   stroke width, but the illusion is there at all scales and the edges must
   subtly become thicker near the node to appear correct to the eye.

## Translations

The plugin's dialog translations are enabled. Currently only english (by default) and french are available. If you want to contribute to translations in other languages, you're welcome to open a ticket, and attach the .po file if possible.
