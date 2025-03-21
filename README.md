# Blender-Navcam-Importer
Addon for Blender that creates Martian surfaces from Mars Rover images (NAvcam, Pancam, Hazcams).

![Curiosity Sol 1051](http://i.imgur.com/DhUrzPi.jpg)

See a movie here: https://vimeo.com/160405895

## Introduction
For autonomous driving on Mars every rover is equipped with a set of (Left and Right) Navigation camera's. From the photo's made with these camera's a depth map is computed which is used by the rover to avoid collisions with rocks or other obstacles. These depth maps, which are basically digitized Martian landscapes, get transmitted back to earth with all other obtained data and after a four month period they appear online in the [Planetary Data System Imaging](http://pds-imaging.jpl.nasa.gov) archive from NASA.
 
The Navcam-importer addon is able to locate and decode the depth maps and import them into Blender. The only thing required is the filename of a valid Left Navcam image to retrieve the corresponding data from the NASA/PDS archive. Example filenames are:  
- for Spirit:        2N227484705MRDAS2JP1981L0M1  
- for Opportunity:   1N142657823MRD3221P1971L0M1
- for Curiosity:     NLB_499684210EDR_F0501222NCAM00290M_

Tip: you can use [PFB converter in this repo](https://github.com/jumpjack/VST-converter) to process .PFB files downloaded from [PDS servers](https://pds-imaging.jpl.nasa.gov/data/mer/spirit/mer2mw_0xxx/data/navcam/site0137/): each PFB contains multiple images/meshes into one single mesh, and the converter extracts the list of images in a format directly usable by this script for importing in Blender.

.PFB files are grouped by "site"; each "site" is a location along rover traverse map: all XYZ files/images/products (and hence all PFB files) created in the frame of same site have the site itself as the origin of reference system, hence they can all be imported together in Blender and be automatically placed in the right position in space.


## Installation
Download the python script (v2 for Blender 2.80+) and install as addon in Blender’s Preference panel. Enable it.
Select the addon from the Import Menu (File > Import) or from the Misc tab in the Tools menu.

## How does it work?
Start the addon and enter or paste the name (or comma-separated names) of a Left Navcam/Pancam/Hazcam image (with or without extension) in the popup dialog and press OK. The addon will automatically download the corresponding depth and image products from the NASA/PDS image archive and stitch the data together into a single UV textured mesh. It will then add a caption and a camera so Blender can render the scene immediately.
  
Note that this process takes a while and Blender is unresponsive during execution. The status of the addon can be checked in the terminal window.

![Collection](http://i.imgur.com/gkcLyFg.jpg)

The resulting mesh, which is in no way scientifically accurate, can contain over a million vertices and will have gaps and glitches. For artistic purposes this addon provides an option to fill small gaps.

Check this [page](https://github.com/phaseIV/Blender-Navcam-Importer/wiki/Instructions) for information about obtaining Navcam image names.

## UPDATES
- 17 Apr 2016: The addon is upgraded with an option to use 16bit RAD images for texturing the mesh.  
- 14 Jan 2019: Rewrote parts to make the addon compatible with Blender 2.8
- July 2022: Added support for Pancam and Hazcam, images; added support for meshes without texture without interrupting execution.

## Notes
The addon caches all downloaded data in Blender’s Temp directory. Texture images will get packed in the Blend file.

Batch import works by pasting a single line with comma seperated image names into the addon popupmenu.

Mars Rover Navcam images are grayscale only. Projecting color images might get implemented in the future.

Recent Navcam image ID’s don’t work because the depth images are not yet available in PDS.  
Check the following links for Navcam/Sol PDS release schedules:  
MSL: http://pds-geosciences.wustl.edu/missions/msl/  
MER: http://pds-geosciences.wustl.edu/missions/mer/  

Credits: NASA/JPL-CALTECH

![Curiosity Sol 440](http://i.imgur.com/efAPdt2.jpg)
