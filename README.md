
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

