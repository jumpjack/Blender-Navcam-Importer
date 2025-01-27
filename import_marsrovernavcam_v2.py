import bpy
import os
import subprocess
import sys
import math
import mathutils
from mathutils import Vector, Quaternion
import struct
import bmesh
from urllib import request
import time
import re
from datetime import datetime


# 0.3.2
# Missing texture is no more critical error: mesh is created without texture
# Even missing XYZ data is not critical, so batch processing will continue with available data

# 0.3.0 by Jumpjack
# Added support for navcam, rear hazcam and front hazcam for MER1/MER2
# Added support for alternate texture (EFF or FFL)
# Added comments/explanations on naming convention



bl_info = {
    "name": "Mars Rover Multicam Import",
    "author": "Jumpjack (credits: Rob Haarsma)",
    "version": (0, 3, 2),
    "blender": (2, 80, 0),
    "location": "File > Import > ...  and/or 3D Window Tools menu > Mars Rover Multicam Import",
    "description": "Creates Martian landscapes from Mars Rover Navcam/Pancam/Hazcam images",
    "warning": "This script produces high poly meshes and saves downloaded data in Temp directory",
    "wiki_url": "https://github.com/jumpjack/Blender-Navcam-Importer",
    "tracker_url": "https://github.com/jumpjack/Blender-Navcam-Importer/issues",
    "category": "Import-Export"}


pdsimg_path = 'https://pds-imaging.jpl.nasa.gov/data/'
# mirror: https://pdsimage2.wr.usgs.gov/data/mer2no/mer2no_0xxx/data/sol1869/rdr/

nasaimg_path = 'https://pds-imaging.jpl.nasa.gov/data/' # 'https://mars.nasa.gov/'
# https://pds-imaging.jpl.nasa.gov/data/mer2-m-navcam-5-xyz-ops-v1.0/mer2no_0xxx/data/
# https://pds-imaging.jpl.nasa.gov/data/mer/mer2no_0xxx/data/

roverDataDir = []
roverImageDir = []
local_data_dir = []
local_file = []

popup_error = None
curve_minval = None
curve_maxval = None

SPIRIT = 1
OPPORTUNITY = 2
CURIOSITY = 3

MER_LENGTH = 27
MSL_LENGTH = 36


class NavcamDialogOperator(bpy.types.Operator):
    bl_idname = "io.navcamdialog_operator"
    bl_label = "Enter Rover Navcam/Pancam image ID"

    navcam_string: bpy.props.StringProperty(name="Image Name", default='')
    fillhole_bool: bpy.props.BoolProperty(name="Fill Gaps (draft)", default = True)
    #filllength_float: bpy.props.FloatProperty(name="Max Fill Length", min=0.001, max=100.0, default=0.6)
    radimage_bool: bpy.props.BoolProperty(name="Use 16bit RAD texture", default = False)

    def execute(self, context):
        ReadNavcamString(self.navcam_string, self.fillhole_bool, self.radimage_bool)
        # navcam_string: one or more image id, comma separated
        # fillhole_bool: flag to attempt filling holes
        # radimage_bool: flag to use 16 bit texture
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=550)


def ReadNavcamString(inString, inFillBool, inRadBool):
    # inString: one or more image id, comma separated
    # inFillBool: flag to attempt filling holes
    # inRadBool: flag to use 16 bit texture

    global local_data_dir, roverDataDir, roverImageDir, popup_error, curve_minval, curve_maxval

    if inString=="": return


    time_start = time.time()

    SetRenderSettings()
    local_data_dir = os.path.join(bpy.context.preferences.filepaths.temporary_directory, 'MarsRoverImages/')

    collString = inString.split(",") # Divide multiple image ids into an array

    # Remove invalid/empty strings
    for i in range(0, len(collString)):
        if(len(collString[i]) == 0): collString.pop(i)

    # Remove spaces,  turn to upper case, remove *.IMG extension if present
    for i in range(0, len(collString)):
        theString = os.path.splitext(collString[i].strip( ' ' ))[0].upper().replace('.IMG','') # case insensitive

        if len(theString) == MER_LENGTH or len(theString) == MSL_LENGTH:
            pass
        else:
            popup_error = 3
            bpy.context.window_manager.popup_menu(draw, title="Name Error", icon='ERROR')
            return

        rover = None
        roverCamera = None

        print(' ');
        print('=============================');
        print('Processing image: ',   theString);

        if theString.startswith( 'N' ):
            rover = CURIOSITY
            
            
        if theString.startswith( '2N' ) :
            rover = SPIRIT
            roverCamera == 'navcam'
            roverDataDir = 'mer/spirit/mer2no_0xxx/data/' #  'mer/mer2no_0xxx/data/'
            roverImageDir = 'mer/spirit/mer2no_0xxx/browse/'  # 'mer/gallery/all/2/n/'  
            print ('Detected image from navcam')
        if theString.startswith( '2P' ) :
            rover = SPIRIT
            roverCamera == 'pancam'
            roverDataDir = 'mer/spirit/mer2po_0xxx/data/' #  'mer/mer2po_0xxx/data/'
            roverImageDir = 'mer/spirit/mer2po_0xxx/browse/' #'mer/gallery/all/2/p/'
            print ('Detected image from PANCAM')
        if theString.startswith( '2F' ) :
            rover = SPIRIT
            roverCamera == 'fhazcam'
            roverDataDir = 'mer/spirit/mer2ho_0xxx/data/' #  'mer/mer2ho_0xxx/data/'
            roverImageDir = 'mer/spirit/mer2ho_0xxx/browse/' #'mer/gallery/all/2/h/'
            print ('Detected image from FRONT HAZCAM')
        if theString.startswith( '2R' ) :
            rover = SPIRIT
            roverCamera == 'rhazcam'
            roverDataDir = 'mer/spirit/mer2ho_0xxx/data/' #'mer/mer2ho_0xxx/data/'
            roverImageDir = 'mer/spirit/mer2ho_0xxx/browse/' #'mer/gallery/all/2/h/'
            print ('Detected image from REAR HAZCAM')
            
            
        if theString.startswith( '1N' ) :
            rover = OPPORTUNITY
            roverCamera == 'navcam'
            roverDataDir = 'mer/opportunity/mer1no_0xxx/data/' #'mer/mer1no_0xxx/data/'
            roverImageDir = 'mer/opportunity/mer1no_0xxx/browse/' # 'mer/gallery/all/1/n/'
            print ('Detected image from navcam')
        if theString.startswith( '1P' ) :
            rover = OPPORTUNITY
            roverCamera == 'pancam'
            roverDataDir = 'mer/opportunity/mer1po_0xxx/data/' #'mer/mer1po_0xxx/data/'
            roverImageDir = 'mer/opportunity/mer1po_0xxx/browse/' # 'mer/gallery/all/1/p/'
            print ('Detected image from PANCAM')
        if theString.startswith( '1F' ) :
            rover = OPPORTUNITY
            roverCamera == 'fhazcam'
            roverDataDir = 'mer/opportunity/mer1ho_0xxx/data/' #'mer/mer1ho_0xxx/data/'
            roverImageDir = 'mer/opportunity/mer1ho_0xxx/browse/' # 'mer/gallery/all/1/h/'
            print ('Detected image from FRONT HAZCAM')
        if theString.startswith( '1R' ) :
            rover = OPPORTUNITY
            roverCamera == 'rhazcam'
            roverDataDir = 'mer/opportunity/mer1ho_0xxx/data/' #'mer/mer1ho_0xxx/data/'
            roverImageDir = 'mer/opportunity/mer1ho_0xxx/browse/' # 'mer/gallery/all/1/h/'
            print ('Detected image from REAR HAZCAM')
            
            
        if rover == None:
            popup_error = 4
            bpy.context.window_manager.popup_menu(draw, title="Name Error", icon='ERROR')
            return

        sol_ref = tosol(rover, theString)

        if rover == CURIOSITY:
            if sol_ref < 1870:
                roverDataDir = 'msl/MSLNAV_1XXX/DATA_V1/'
                roverImageDir = 'msl/MSLNAV_1XXX/EXTRAS_V1/FULL/'
            else:
                roverDataDir = 'msl/MSLNAV_1XXX/DATA/'
                roverImageDir = 'msl/MSLNAV_1XXX/EXTRAS/FULL/'

        print( '\nConstructing mesh %d/%d, sol %d, name %s' %( i + 1, len(collString), sol_ref, theString) )
        print ('Texture cache folder: ', roverImageDir);
        print ('XYZ data cache folder: ', roverDataDir);
        curve_minval = 0.0
        curve_maxval = 1.0

        if inRadBool:
            image_16bit_texture_filename = get_16bit_texture_image(rover, sol_ref, theString, roverImageDir)
            image_texture_filename = convert_to_png(image_16bit_texture_filename)
        else:
            image_texture_filename = get_texture_image(rover, sol_ref, theString)

        print('Texture selected: ', image_texture_filename)
        if (image_texture_filename == None):
            print ('Texture not found, going on...') #Example: 2N295212876EFFB1DNP1950L0M1

        image_depth_filename = get_depth_image(rover, sol_ref, theString)
        if (image_depth_filename == None):
            print (' ')
            print (' >>>>>>> ERROR <<<<<<<<< XYZ file not found for id:', theString)
            print (' ')
            #example: 2N295460956EFFB1DNP1983L0M1 (not in sol 1904 but 1905)
        else:
          create_mesh_from_depthimage(rover, sol_ref, image_depth_filename, image_texture_filename, inFillBool, inRadBool)

        # For color images we need 3 images, one per band. Example for MER:
        # 1p579517559mrdd2fap2377l2m1 - Band 2 at 753nm (=R)
        # 1p579517698mrdd2fap2377l5m1 - Band 5 at 535nm (=G)
        # 1p579517712mrdd2fap2377l7m1 - Band 7 at 440nm (=B)
        # SCLK: different
        # sequence number: same (p2377)



    elapsed = float(time.time() - time_start)
    print("Script execution time: %s" % time.strftime('%H:%M:%S', time.gmtime(elapsed)))


def SetRenderSettings():
    rnd = bpy.data.scenes[0].render
    rnd.resolution_x = 1024
    rnd.resolution_y = 1024
    rnd.resolution_percentage = 100
    rnd.tile_x = 512
    rnd.tile_y = 512
    wrld = bpy.context.scene.world
    nt = bpy.data.worlds[wrld.name].node_tree
    backNode = nt.nodes['Background']
    backNode.inputs[0].default_value = (0.02, 0.02, 0.02, 1)


def download_file(url):
    global localfile
    proper_url = url.replace('\\','/')
    print('**DOWNLOAD:', proper_url)

    if sys.platform == 'darwin':
        try:
            out = subprocess.check_output(['curl', '-I', proper_url])
            print('**DOWNLOAD OUT:')
            print(out)

            if out.decode().find('200 OK') > 0:
                subprocess.call(['curl', '-o', localfile, '-L', proper_url])
                return True
            else:
                print('Fail to reach a server.\n\n{}'.format(out.decode()))
                return False

        except subprocess.CalledProcessError as e:
            print('Subprocess failed:\nReturncode: {}\n\nOutput:{}'.format(e.returncode, e.output))
            return False

    else:
        try:
            page = request.urlopen(proper_url)

            if page.getcode() is not 200:
                return False

            request.urlretrieve(proper_url, localfile)
            return True

        except:
            return False


def tosol(rover, nameID):

	# MER naming convention:
	# https://pds-imaging.jpl.nasa.gov/data/mer2-m-navcam-5-xyz-ops-v1.0/mer2no_0xxx/document/CAMSIS_latest.PDF

    # 2N290962708XYLB0HMP0755L0M2
    # 0:     2         = MER2
    # 1:     N         = Navcam
    # 2-10:  290962708 = Spacecraft clock
    # 11-13: XYL       = XYL product
    # 14-15: B0        = site
    # 16-17: HM        = drive/position w.r.t site
    # 18-22: P0755     = sequence (“P”  -  PMA & RemoteSensing instr.  (Pancam, Navcam, Hazcam, MI, Mini-TES)
    # 23:    L         = left
    # 24:    0         = filter
    # 25:    M         = Author (MIPL)
    # 26:    2         = Product version

    # Sequence details:
    # ( https://pds-imaging.jpl.nasa.gov/data/mer/opportunity/mer1ho_0xxx/document/CAMSIS_latest.PDF )
    # seq    =    (1 alpha character plus 4 integers)  Sequence identifier.  Denotes a group of related
    # commands used as keys for the Ops processing.
    #
    # Valid values for character (position 1) in field:
    #
    # “C”  -  Cruise
    # “D”  -  IDD & RAT
    # “E”  -  Engineering
    # “F”  -  Flight Software (Seq rejected)
    # “G”  -  (spare)
    # “K”  -  (spare)
    # “M”  -  Master (Surface only)
    # “N”  -  In-Situ instr. (APXS, MB, MI)
    # “P”  -  PMA & Remote Sensing instr.  (Pancam, Navcam, Hazcam, MI, Mini-TES)
    # “R”  -  Rover Driving
    # “S”  -  Submaster
    # “T”  -  Test
    # “W” -  Seq triggered by a Commun. Window
    # “X”  -  Contingency
    # “Y”  -  (spare)
    # “Z”  -  SCM Seq’s

    # origin: https://github.com/natronics/MSL-Feed/blob/master/nasa.py
    # function hacked to return sol from image filename
    craft_time = None

    if rover == CURIOSITY:
        craft_time = nameID[4:13]
    if rover == OPPORTUNITY or rover == SPIRIT:
        craft_time = nameID[2:11] 

    s = int(craft_time)
    MSD = (s/88775.244) + 44795.9998

    sol = MSD - 49269.2432411704
    sol = sol + 1  # for sol 0
    sol = int(math.ceil(sol))

    deviate = None

    if rover == CURIOSITY:
        deviate = -6
    if rover == OPPORTUNITY:
        deviate = 3028
    if rover == SPIRIT:
        deviate = 3048

    return sol+deviate


def get_texture_image(rover, sol, imgname):
    global roverImageDir, local_data_dir, localfile

    if rover == CURIOSITY:
        if sol > 450:
            texname = '%s.PNG' %( imgname )
        else:
            texname = '%s.JPG' %( imgname )
    else:
        texname = '%s.img.JPG' %( imgname )

    s = list( texname )

    if rover == CURIOSITY:
        s[13] = 'R'
        s[14] = 'A'
        s[15] = 'S'
        s[35] = '1'
    else:
        # Full frame EDR “EFF”
        # Full frame EDR “EFF” n/a
        # Radiometrically-corrected RDR calibrated to absolute radiance units “RAD” “RAL”
        # MIPLRAD Radiometrically-corrected RDR calibrated to absolute radiance units, specific to archived datasets only “MRD” “MRL”
        # Rad-corrected Float (32-bit) RDR “RFD” “RFL”
        # Radiometrically-corrected RDR calibrated to I/F radiance factor “IOF” “IOL”
        # Rad-corrected Float (32-bit) RDR calibrated to I/F radiance factor “IFF” “IFL”
        # Sum of Rad-corrected Float (32-bit) RDR calibrated to I/F radiance factor, produced by MI Athena team “IFS” n/a

        if s[18] == 'F' or s[18] == 'f':  # ? char 18 is always "P" for images sequences (“P”  -  PMA & Remote Sensing instr.  (Pancam, Navcam, Hazcam, MI, Mini-TES)
            #mer downsampled??
            s[11] = 'e'
            s[12] = 'd'
            s[13] = 'n'
            s[25] = 'm'  # Useless? "M" stands for "MIPS", author of image, and is contant
            s[26] = '1'  # Force use of version 1 of texture
        else:
            s[11] = 'e'
            s[12] = 'f'
            s[13] = 'f'
            s[25] = 'm'  # Useless? "M" stands for "MIPS", author of image, and is contant
            s[26] = '1'  # Force use of version 1 of texture

    imagename = '%s' % "".join(s)
    print ('local_data_dir :', local_data_dir)
    print ('roverImageDir :', roverImageDir)
    print ('sol :', sol )
    print ('imagename :', imagename)
    # imgfilename = os.path.join(local_data_dir, roverImageDir, '%05d' %(sol), imagename )
    imgfilename = os.path.join(local_data_dir, roverImageDir, 'sol%04d' %(sol), 'rdr', imagename )

    print('Looking for EFF texture in cache: ', imgfilename)

    if os.path.isfile(imgfilename):
        print('   EFF texture found, loading...')
        return imgfilename
    else :
      s[11] = 'f'
      s[12] = 'f'
      s[13] = 'l'
      s[25] = 'm'  
      s[26] = '1'  # Force use of version 1 of texture
      imagename2 = '%s' % "".join(s)
      imgfilename2 = os.path.join(local_data_dir, roverImageDir, 'sol%04d' %(sol), 'rdr', imagename2 )
      print('#### EFF texture not found; looking for alternative (FFL) texture in cache: ', imgfilename2)
      if os.path.isfile(imgfilename2):
          print('   ----> FFL texture found, loading...')
          return imgfilename2
      else :
        s[11] = 'm'
        s[12] = 'r'
        s[13] = 'l'
        s[25] = 'm'
        s[26] = '1'  # Force use of version 1 of texture
        imagename3 = '%s' % "".join(s)
        imgfilename3 = os.path.join(local_data_dir, roverImageDir, 'sol%04d' %(sol), 'rdr', imagename3 )
        print('#### MRL texture not found; looking for alternative (MRL) texture in cache: ', imgfilename3)
        if os.path.isfile(imgfilename3):
            print('   ----> MRL texture found.')
            return imgfilename3
        else :
            print ('##!## I give up, no texture available in cache, loking online....')

    # Nothing in cache: try downloading...
    
    print ('local_data_dir=',local_data_dir)
    print ('os.path.dirname(local_data_dir)=',os.path.dirname(local_data_dir))
    print ('roverImageDir=',roverImageDir)
    print ('sol=','sol%04d' %( sol ))
    retrievedir = os.path.join(os.path.dirname(local_data_dir), roverImageDir, 'sol%04d' %( sol ) , 'rdr')
    print ('Texture files will be downloaded into ', retrievedir)
    if not os.path.exists(retrievedir):
        os.makedirs(retrievedir)

    # Try first with EFF texture:
    localfile = imgfilename
    if rover == OPPORTUNITY or rover == SPIRIT:
        # https://pds-imaging.jpl.nasa.gov/data/mer/spirit/mer2no_0xxx/browse/sol0005/rdr/
        # nasaimg_path: https://pds-imaging.jpl.nasa.gov/data/
        # roverImageDir: mer/spirit/mer2no_0xxx/browse/
        remotefile = os.path.join(os.path.dirname(nasaimg_path), roverImageDir, 'sol%04d' %(sol), 'rdr', imagename.lower() )
        
    if rover == CURIOSITY:
        remotefile = os.path.join(os.path.dirname(pdsimg_path), roverImageDir, 'SOL%05d' %(sol), imagename )

    print('Trying to download EFF texture: ', remotefile)
    print('to local texture folder: ', retrievedir)
    print('as : ', localfile)

    result = download_file(remotefile)
    if(result == False):
      # No EFF texture, try with FFL:
      print ('#### EFF texture not found online.')
      localfile = imgfilename2
      if rover == OPPORTUNITY or rover == SPIRIT:
          remotefile = os.path.join(os.path.dirname(nasaimg_path), roverImageDir, 'sol%04d' %(sol), 'rdr', imagename2.lower() )
      if rover == CURIOSITY:
          remotefile = os.path.join(os.path.dirname(pdsimg_path), roverImageDir, 'SOL%05d' %(sol), imagename2 )
      imgfilename = imgfilename2 # FFL

      print('Trying to download FFL texture: ', remotefile)
      print('to local texture folder: ', retrievedir)
      print('as : ', localfile)

      result = download_file(remotefile) # FFL
      if(result == False):
        print ('#### FFL texture not found online.')
        localfile = imgfilename3
        if rover == OPPORTUNITY or rover == SPIRIT:
            remotefile = os.path.join(os.path.dirname(nasaimg_path), roverImageDir, 'sol%04d' %(sol), 'rdr', imagename3.lower() )
        if rover == CURIOSITY:
            remotefile = os.path.join(os.path.dirname(pdsimg_path), roverImageDir, 'SOL%05d' %(sol), imagename3 )

        imgfilename = imgfilename3
        print('Trying to download MRL texture: ', remotefile)
        print('to local texture folder: ', retrievedir)
        print('as : ', localfile)
        result = download_file(remotefile) # MRL
        if(result == False):
          print ('#### MRL texture not found, I give up, cannot find any texture online.')
          return None
        else :
          print('  ---> MRL texture successfully downloaded.')
          imgfilename = os.path.join(local_data_dir, roverImageDir, 'sol%04d' %(sol), 'rdr', imagename3 )
          return imgfilename # MRL
      else :
        print('  ---> FFL texture successfully downloaded.')
        imgfilename = os.path.join(local_data_dir, roverImageDir, 'sol%04d' %(sol), 'rdr', imagename2 )
        return imagename #FFL texture
    else :
      print('  ---> EFF texture successfully downloaded.')
      imgfilename = os.path.join(local_data_dir, roverImageDir, 'sol%04d' %(sol), 'rdr', imagename )
      return imgfilename #EFF texture


#    if os.path.isfile(localfile):
#        print ('Texture file successfully downloaded: ',imgfilename)
#        return imgfilename


def get_16bit_texture_image(rover, sol, imgname):
    global roverImageDir, local_data_dir, localfile

    texname = '%s.IMG' %( imgname )
    s = list( texname )

    if rover == CURIOSITY:
        s[13] = 'R'
        s[14] = 'A'
        s[15] = 'D'
        s[35] = '1'
    else:
        s[11] = 'm'
        s[12] = 'r'
        s[13] = 'd'
        s[25] = 'm'

    imagename = '%s' % "".join(s)
    imgfilename = os.path.join(local_data_dir, roverDataDir, 'sol%05d' %(sol), imagename )

    if os.path.isfile(imgfilename):
        print('Loading 16 bit texture (rad) from cache: ', imgfilename)
        return imgfilename

    retrievedir = os.path.join(os.path.dirname(local_data_dir), roverImageDir, 'sol%04d' %( sol ) , 'rdr')
    print ('16 bit texture files (rad) are cached into ', retrievedir)
    if not os.path.exists(retrievedir):
        os.makedirs(retrievedir)

    localfile = imgfilename

    if rover == OPPORTUNITY or rover == SPIRIT:
        remotefile = os.path.join(os.path.dirname(pdsimg_path), roverDataDir, 'sol%04d' %(sol), 'rdr', imagename.lower() )
    if rover == CURIOSITY:
        remotefile = os.path.join(os.path.dirname(pdsimg_path), roverDataDir, 'SOL%05d' %(sol), imagename )

    print('Downloading 16 bit texture (rad): ', remotefile)

    result = download_file(remotefile)
    if(result == False):
        return None

    if os.path.isfile(localfile):
        return imgfilename


def get_depth_image(rover, sol, imgname):
    global roverDataDir, local_data_dir, localfile

    xyzname = '%s.IMG' %( imgname )
    s = list( xyzname )

    if rover == CURIOSITY:
        s[13] = 'X'
        s[14] = 'Y'
        s[15] = 'Z'
        s[35] = '1'
    else :
        s[11] = 'x'
        s[12] = 'y'
        s[13] = 'l'
        s[25] = 'm' 

    xyzname = '%s' % "".join(s)
    xyzfilename = os.path.join(local_data_dir, roverDataDir, 'sol%04d' %(sol), 'rdr', xyzname )

    print ('XYZ data file:', xyzfilename)
    print ('Searching in cache....')

    if os.path.isfile(xyzfilename):
        print('  ---> OK, XYZ found in cache')
        return xyzfilename

    print ('#### XYZ not found in cache, looking online...')
    retrievedir = os.path.join(local_data_dir, roverDataDir, 'sol%04d' %(sol) , 'rdr')

    if not os.path.exists(retrievedir):
        os.makedirs(retrievedir)

    localfile = xyzfilename

    if rover == OPPORTUNITY or rover == SPIRIT:
        remotefile = os.path.join(os.path.dirname(pdsimg_path), roverDataDir, 'sol%04d' %(sol), 'rdr', xyzname.lower() )
    if rover == CURIOSITY:
        remotefile = os.path.join(os.path.dirname(pdsimg_path), roverDataDir, 'SOL%05d' %(sol), xyzname )

    print('Trying to download  xyz: ', remotefile)
    print('to local XYZ folder: ', retrievedir)
    print('as: ', localfile)

    result = download_file(remotefile)
    if(result == False):
        print('>>>>>>> Download of XYZ failed: ',remotefile)
        return None

    print('  ---> XYZ download successful.')

    if os.path.isfile(localfile):
        print('Local file:',localfile)
        return xyzfilename
    else :
        print('>>> ERROR >>>> Can\'t find local file just downloaded!:', localfile)
        return None


def convert_to_png(image_16bit_texture_filename):
    global curve_minval, curve_maxval

    LINES = LINE_SAMPLES = SAMPLE_BITS = BYTES = 0
    SAMPLE_TYPE = ""

    FileAndPath = image_16bit_texture_filename
    FileAndExt = os.path.splitext(FileAndPath)

    print('creating png...')

    # Open the img file (ascii label part)
    try:
        if FileAndExt[1].isupper():
            f = open(FileAndExt[0] + ".IMG", 'r')
        else:
            f = open(FileAndExt[0] + ".img", 'r')
    except:
        return

    block = ""
    OFFSET = 0
    for line in f:
        if line.strip() == "END":
            break
        tmp = line.split("=")
        if tmp[0].strip() == "OBJECT" and tmp[1].strip() == "IMAGE":
            block = "IMAGE"
        elif tmp[0].strip() == "END_OBJECT" and tmp[1].strip() == "IMAGE":
            block = ""
        if tmp[0].strip() == "OBJECT" and tmp[1].strip() == "IMAGE_HEADER":
            block = "IMAGE_HEADER"
        elif tmp[0].strip() == "END_OBJECT" and tmp[1].strip() == "IMAGE_HEADER":
            block = ""

        if block == "IMAGE":
            if line.find("LINES") != -1 and not(line.startswith("/*")):
                tmp = line.split("=")
                LINES = int(tmp[1].strip())
            elif line.find("LINE_SAMPLES") != -1 and not(line.startswith("/*")):
                tmp = line.split("=")
                LINE_SAMPLES = int(tmp[1].strip())
            elif line.find("SAMPLE_TYPE") != -1 and not(line.startswith("/*")):
                tmp = line.split("=")
                SAMPLE_TYPE = tmp[1].strip()
            elif line.find("SAMPLE_BITS") != -1 and not(line.startswith("/*")):
                tmp = line.split("=")
                SAMPLE_BITS = int(tmp[1].strip())

        if block == "IMAGE_HEADER":
            if line.find("BYTES") != -1 and not(line.startswith("/*")):
                tmp = line.split("=")
                BYTES = int(tmp[1].strip())

    f.close

    # Open the img file (binary data part)
    try:
        if FileAndExt[1].isupper():
            f2 = open(FileAndExt[0] + ".IMG", 'rb')
        else:
            f2 = open(FileAndExt[0] + ".img", 'rb')
    except:
        return

    edit = f2.read()
    meh = edit.find(b'LBLSIZE')
    f2.seek( meh + BYTES)

    bands = []
    for bandnum in range(0, 1):

        bands.append([])
        for linenum in range(0, LINES):

            bands[bandnum].append([])
            for pixnum in range(0, LINE_SAMPLES):

                dataitem = f2.read(2)
                if (dataitem == ""):
                    print ('ERROR, Ran out of data to read before we should have')

                bands[bandnum][linenum].append(struct.unpack(">H", dataitem)[0])

    f2.close

    pixels = [None] * LINES * LINE_SAMPLES

    curve_minval = 1.0
    curve_maxval = 0.0

    for j in range(0, LINES):
        for k in range(0, LINE_SAMPLES):

            r = g = b = float(bands[0][LINES-1 - j][k] & 0xffff )  / (32768*2)
            a = 1.0
            pixels[(j * LINES) + k] = [r, g, b, a]

            if r > curve_maxval: curve_maxval = r
            if r < curve_minval: curve_minval = r

    del bands

    pixels = [chan for px in pixels for chan in px]
    pngname = FileAndExt[0] + '.PNG'

    # modify scene for png export
    scene = bpy.data.scenes[0]
    settings = scene.render.image_settings
    settings.color_depth = '16'
    settings.color_mode = 'BW'
    settings.file_format = 'PNG'

    image = bpy.data.images.new(os.path.basename(FileAndExt[0]), LINES, LINE_SAMPLES, float_buffer=True)
    image.pixels = pixels
    image.file_format = 'PNG'
    image.save_render(pngname)

    settings.color_depth = '8'
    settings.color_mode = 'RGBA'

    # remove converted image from Blender, it will be reloaded
    bpy.data.images.remove(image)
    del pixels

    return pngname


# -----------------------------------------------------------------------------
# Cycles/Eevee routines adapted from: https://github.com/florianfelix/io_import_images_as_planes_rewrite

def get_input_nodes(node, links):
    """Get nodes that are a inputs to the given node"""
    # Get all links going to node.
    input_links = {lnk for lnk in links if lnk.to_node == node}
    # Sort those links, get their input nodes (and avoid doubles!).
    sorted_nodes = []
    done_nodes = set()
    for socket in node.inputs:
        done_links = set()
        for link in input_links:
            nd = link.from_node
            if nd in done_nodes:
                # Node already treated!
                done_links.add(link)
            elif link.to_socket == socket:
                sorted_nodes.append(nd)
                done_links.add(link)
                done_nodes.add(nd)
        input_links -= done_links
    return sorted_nodes


def auto_align_nodes(node_tree):
    """Given a shader node tree, arrange nodes neatly relative to the output node."""
    x_gap = 300
    y_gap = 180
    nodes = node_tree.nodes
    links = node_tree.links
    output_node = None
    for node in nodes:
        if node.type == 'OUTPUT_MATERIAL' or node.type == 'GROUP_OUTPUT':
            output_node = node
            break

    else:  # Just in case there is no output
        return

    def align(to_node):
        from_nodes = get_input_nodes(to_node, links)
        for i, node in enumerate(from_nodes):
            node.location.x = min(node.location.x, to_node.location.x - x_gap)
            node.location.y = to_node.location.y
            node.location.y -= i * y_gap
            node.location.y += (len(from_nodes) - 1) * y_gap / (len(from_nodes))
            align(node)

    align(output_node)


def clean_node_tree(node_tree):
    """Clear all nodes in a shader node tree except the output. Returns the output node"""
    nodes = node_tree.nodes
    for node in list(nodes):  # copy to avoid altering the loop's data source
        if not node.type == 'OUTPUT_MATERIAL':
            nodes.remove(node)

    return node_tree.nodes[0]


def get_shadeless_node(dest_node_tree):
    """Return a "shadless" cycles/eevee node, creating a node group if nonexistent"""
    try:
        node_tree = bpy.data.node_groups['NAV_SHADELESS']

    except KeyError:
        # need to build node shadeless node group
        node_tree = bpy.data.node_groups.new('NAV_SHADELESS', 'ShaderNodeTree')
        output_node = node_tree.nodes.new('NodeGroupOutput')
        input_node = node_tree.nodes.new('NodeGroupInput')

        node_tree.outputs.new('NodeSocketShader', 'Shader')
        node_tree.inputs.new('NodeSocketColor', 'Color')

        # This could be faster as a transparent shader, but then no ambient occlusion
        diffuse_shader = node_tree.nodes.new('ShaderNodeBsdfDiffuse')
        node_tree.links.new(diffuse_shader.inputs[0], input_node.outputs[0])

        emission_shader = node_tree.nodes.new('ShaderNodeEmission')
        node_tree.links.new(emission_shader.inputs[0], input_node.outputs[0])

        light_path = node_tree.nodes.new('ShaderNodeLightPath')
        is_glossy_ray = light_path.outputs['Is Glossy Ray']
        is_shadow_ray = light_path.outputs['Is Shadow Ray']
        ray_depth = light_path.outputs['Ray Depth']
        transmission_depth = light_path.outputs['Transmission Depth']

        unrefracted_depth = node_tree.nodes.new('ShaderNodeMath')
        unrefracted_depth.operation = 'SUBTRACT'
        unrefracted_depth.label = 'Bounce Count'
        node_tree.links.new(unrefracted_depth.inputs[0], ray_depth)
        node_tree.links.new(unrefracted_depth.inputs[1], transmission_depth)

        refracted = node_tree.nodes.new('ShaderNodeMath')
        refracted.operation = 'SUBTRACT'
        refracted.label = 'Camera or Refracted'
        refracted.inputs[0].default_value = 1.0
        node_tree.links.new(refracted.inputs[1], unrefracted_depth.outputs[0])

        reflection_limit = node_tree.nodes.new('ShaderNodeMath')
        reflection_limit.operation = 'SUBTRACT'
        reflection_limit.label = 'Limit Reflections'
        reflection_limit.inputs[0].default_value = 2.0
        node_tree.links.new(reflection_limit.inputs[1], ray_depth)

        camera_reflected = node_tree.nodes.new('ShaderNodeMath')
        camera_reflected.operation = 'MULTIPLY'
        camera_reflected.label = 'Camera Ray to Glossy'
        node_tree.links.new(camera_reflected.inputs[0], reflection_limit.outputs[0])
        node_tree.links.new(camera_reflected.inputs[1], is_glossy_ray)

        shadow_or_reflect = node_tree.nodes.new('ShaderNodeMath')
        shadow_or_reflect.operation = 'MAXIMUM'
        shadow_or_reflect.label = 'Shadow or Reflection?'
        node_tree.links.new(shadow_or_reflect.inputs[0], camera_reflected.outputs[0])
        node_tree.links.new(shadow_or_reflect.inputs[1], is_shadow_ray)

        shadow_or_reflect_or_refract = node_tree.nodes.new('ShaderNodeMath')
        shadow_or_reflect_or_refract.operation = 'MAXIMUM'
        shadow_or_reflect_or_refract.label = 'Shadow, Reflect or Refract?'
        node_tree.links.new(shadow_or_reflect_or_refract.inputs[0], shadow_or_reflect.outputs[0])
        node_tree.links.new(shadow_or_reflect_or_refract.inputs[1], refracted.outputs[0])

        mix_shader = node_tree.nodes.new('ShaderNodeMixShader')
        node_tree.links.new(mix_shader.inputs[0], shadow_or_reflect_or_refract.outputs[0])
        node_tree.links.new(mix_shader.inputs[1], diffuse_shader.outputs[0])
        node_tree.links.new(mix_shader.inputs[2], emission_shader.outputs[0])

        node_tree.links.new(output_node.inputs[0], mix_shader.outputs[0])

        auto_align_nodes(node_tree)

    group_node = dest_node_tree.nodes.new("ShaderNodeGroup")
    group_node.node_tree = node_tree

    return group_node


def create_cycles_texnode(context, node_tree, image):
    tex_image = node_tree.nodes.new('ShaderNodeTexImage')
    tex_image.image = image
    tex_image.show_texture = True
    image_user = tex_image.image_user
    tex_image.extension = 'CLIP'  # Default of "Repeat" can cause artifacts
    return tex_image


def create_cycles_material(context, image):
    global curve_minval, curve_maxval

    name_compat = bpy.path.display_name_from_filepath(image.filepath)
    material = None
    if not material:
        material = bpy.data.materials.new(name=name_compat)

    material.use_nodes = True
    node_tree = material.node_tree
    out_node = clean_node_tree(node_tree)

    tex_image = create_cycles_texnode(context, node_tree, image)

    core_shader = get_shadeless_node(node_tree)

    curvenode = node_tree.nodes.new('ShaderNodeRGBCurve')
    curvenode.mapping.curves[3].points[0].location.x = curve_minval
    curvenode.mapping.curves[3].points[0].location.y = 0.0
    curvenode.mapping.curves[3].points[1].location.x = curve_maxval
    curvenode.mapping.curves[3].points[1].location.y = 1.0
    curvenode.mapping.update()

    # Connect color from texture to curves
    node_tree.links.new(curvenode.inputs[1], tex_image.outputs[0])

    #Connect color from curves to shadeless
    node_tree.links.new(core_shader.inputs[0], curvenode.outputs[0])
    node_tree.links.new(out_node.inputs[0], core_shader.outputs[0])

    auto_align_nodes(node_tree)
    return material


def create_named_material(context, name):
    name_compat = name
    material = None
    if not material:
        material = bpy.data.materials.new(name=name_compat)

    material.use_nodes = True
    node_tree = material.node_tree
    out_node = clean_node_tree(node_tree)

    core_shader = get_shadeless_node(node_tree)
    core_shader.inputs[0].default_value = (1, 1, 1, 1)

    # Connect color from texture
    node_tree.links.new(out_node.inputs[0], core_shader.outputs[0])

    auto_align_nodes(node_tree)
    return material

# -----------------------------------------------------------------------------


def find_collection(context, item):
    collections = item.users_collection
    if len(collections) > 0:
        return collections[0]
    return context.scene.collection


def get_collection(name):
    if bpy.data.collections.get(name) is None:
        new_collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(new_collection)
        return new_collection
    else:
        return bpy.data.collections.get(name)


def create_mesh_from_depthimage(rover, sol, image_depth_filename, image_texture_filename, do_fill, do_rad):
    # snippets used from:
    # https://svn.blender.org/svnroot/bf-extensions/contrib/py/scripts/addons/io_import_LRO_Lola_MGS_Mola_img.py
    # https://arsf-dan.nerc.ac.uk/trac/attachment/wiki/Processing/SyntheticDataset/data_handler.py

    global curve_minval, curve_maxval

    bRoverVec = Vector((0.0, 0.0, 0.0))

    if image_depth_filename == '':
        return

    creation_date = None
    LINES = LINE_SAMPLES = SAMPLE_BITS = 0
    SAMPLE_TYPE = ""

    FileAndPath = image_depth_filename
    FileAndExt = os.path.splitext(FileAndPath)

    print('Creating mesh...')

    # Open the img label file (ascii label part)
    try:
        if FileAndExt[1].isupper():
            f = open(FileAndExt[0] + ".IMG", 'r')
        else:
            f = open(FileAndExt[0] + ".img", 'r')
    except:
        return

    block = ""
    OFFSET = 0
    for line in f:
        if line.strip() == "END":
            break
        tmp = line.split("=")
        if tmp[0].strip() == "OBJECT" and tmp[1].strip() == "IMAGE":
            block = "IMAGE"
        elif tmp[0].strip() == "END_OBJECT" and tmp[1].strip() == "IMAGE":
            block = ""
        if tmp[0].strip() == "OBJECT" and tmp[1].strip() == "IMAGE_HEADER":
            block = "IMAGE_HEADER"
        elif tmp[0].strip() == "END_OBJECT" and tmp[1].strip() == "IMAGE_HEADER":
            block = ""
        if tmp[0].strip() == "GROUP" and tmp[1].strip() == "ROVER_COORDINATE_SYSTEM":
            block = "ROVER_COORDINATE_SYSTEM"
        elif tmp[0].strip() == "END_GROUP" and tmp[1].strip() == "ROVER_COORDINATE_SYSTEM":
            block = ""

        elif tmp[0].strip() == "START_TIME":
            creation_date = str(tmp[1].strip())

        if block == "IMAGE":
            if line.find("LINES") != -1 and not(line.startswith("/*")):
                tmp = line.split("=")
                LINES = int(tmp[1].strip())
            elif line.find("LINE_SAMPLES") != -1 and not(line.startswith("/*")):
                tmp = line.split("=")
                LINE_SAMPLES = int(tmp[1].strip())
            elif line.find("SAMPLE_TYPE") != -1 and not(line.startswith("/*")):
                tmp = line.split("=")
                SAMPLE_TYPE = tmp[1].strip()
            elif line.find("SAMPLE_BITS") != -1 and not(line.startswith("/*")):
                tmp = line.split("=")
                SAMPLE_BITS = int(tmp[1].strip())

        if block == "IMAGE_HEADER":
            if line.find("BYTES") != -1 and not(line.startswith("/*")):
                tmp = line.split("=")
                BYTES = int(tmp[1].strip())

        if block == "ROVER_COORDINATE_SYSTEM":
            if line.find("ORIGIN_OFFSET_VECTOR") != -1 and not(line.startswith("/*")):
                tmp = line.split("=")
                ORIGIN_OFFSET_VECTOR = str(tmp[1].strip())

                fline = re.sub('[(!@#$)]', '', ORIGIN_OFFSET_VECTOR)
                pf = fline.strip().split(",")

                bRoverVec[:] = float(pf[1]), float(pf[0]), -float(pf[2])

    f.close

    # Open the img label file (binary data part)
    try:
        if FileAndExt[1].isupper():
            f2 = open(FileAndExt[0] + ".IMG", 'rb')
        else:
            f2 = open(FileAndExt[0] + ".img", 'rb')
    except:
        return

    edit = f2.read()
    meh = edit.find(b'LBLSIZE')
    f2.seek( meh + BYTES)

    # Create a list of bands containing an empty list for each band.
    bands = []

    # Each band of the image contains a sequence of Float32 IEEE754 (4 bytes); byte order 
    # is specified in PDS label and Vicar label at the beginning of the file.
    # Band 0 = X, Band 1 = Y, Band 2 = Z.
    # Band length = bytes_per_sample * lines * samples	= 4 * lines * samples
	   

    # Read data for each band at a time
    for bandnum in range(0, 3):
        bands.append([])

        for linenum in range(0, LINES):

            bands[bandnum].append([])

            for pixnum in range(0, LINE_SAMPLES):

                # Read one data item (pixel) from the data file.
                dataitem = f2.read(4)

                if (dataitem == ""):
                    print ('ERROR, Ran out of data to read before we should have')

                # If everything worked, unpack the binary value and store it in the appropriate pixel value
                bands[bandnum][linenum].append(struct.unpack('>f', dataitem)[0])

    f2.close

    Vertex = []
    Faces = []

    nulvec = Vector((0.0,0.0,0.0))

    for j in range(0, LINES):
        for k in range(0, LINE_SAMPLES):
            vec = Vector((float(bands[1][j][k]), float(bands[0][j][k]), float(-bands[2][j][k])))  # Rover Z axis points downwards, hence invert Z
            vec = vec*0.1
            Vertex.append(vec)

    del bands

    #simple dehole (bridge)
    #max_fill_length = fill_length
    max_fill_length = 0.6
    if(do_fill):
        for j in range(0, LINES-1):
            for k in range(0, LINE_SAMPLES-1):
                if Vertex[j * LINE_SAMPLES + k] != nulvec:
                    m = 1
                    while Vertex[(j + m) * LINE_SAMPLES + k] == nulvec and (j + m) < LINES-1:
                        m = m + 1

                    if m != 1 and Vertex[(j + m) * LINE_SAMPLES + k] != nulvec:
                        VertexA = Vertex[j * LINE_SAMPLES + k]
                        VertexB = Vertex[(j + m) * LINE_SAMPLES + k]
                        sparevec = VertexB - VertexA
                        if sparevec.length < max_fill_length:
                            for n in range(0, m):
                                Vertex[(j + n) * LINE_SAMPLES + k] = VertexA + (sparevec / m) * n

    for j in range(0, LINES-1):
        for k in range(0, LINE_SAMPLES-1):
            Faces.append(( (j * LINE_SAMPLES + k), (j * LINE_SAMPLES + k + 1), ((j + 1) * LINE_SAMPLES + k + 1), ((j + 1) * LINE_SAMPLES + k) ))

    os.path.basename(FileAndExt[0])
    TARGET_NAME = '%s-%s' %(sol, os.path.basename(FileAndExt[0]))
    mesh = bpy.data.meshes.new(TARGET_NAME)
    TARGET_NAME = mesh.name
    mesh.from_pydata(Vertex, [], Faces)

    del Vertex
    del Faces
    mesh.update()


    ob_new = bpy.data.objects.new(TARGET_NAME, mesh)
    ob_new.data = mesh

    theSolCollection = get_collection('Sol%s' %(sol))
    theSolCollection.objects.link(ob_new)
    ob_new.select_set(state=True)
    bpy.context.view_layer.objects.active = ob_new

    obj = bpy.context.object

    if image_texture_filename != None :
      ####### ADD TEXTURE ########
      print('Texturing mesh...')
      try:
          with open(image_texture_filename):
              img = bpy.data.images.load(image_texture_filename)
              img.pack()

              engine = bpy.context.scene.render.engine
              if engine in {'CYCLES', 'BLENDER_EEVEE', 'BLENDER_OPENGL'}:
                  material = create_cycles_material(bpy.context, img)

              # add material to object
              obj.data.materials.append(material)

              me = obj.data
              #me.show_double_sided = True
              bpy.ops.mesh.uv_texture_add()

              uvteller = 0

              #per face !
              for j in range(0, LINES -1):
                  for k in range(0, LINE_SAMPLES-1):
                      tc1 = Vector(((1.0 / LINE_SAMPLES) * k, 1.0 - (1.0 / LINES) * j))
                      tc2 = Vector(((1.0 / LINE_SAMPLES) * (k + 1), 1.0 - (1.0 / LINES) * j))
                      tc3 = Vector(((1.0 / LINE_SAMPLES) * (k + 1), 1.0 - (1.0 / LINES) * (j + 1)))
                      tc4 = Vector(((1.0 / LINE_SAMPLES) * k, 1.0 - (1.0 / LINES) * (j + 1)))

                      bpy.data.objects[TARGET_NAME].data.uv_layers[0].data[uvteller].uv = tc1
                      uvteller = uvteller + 1
                      bpy.data.objects[TARGET_NAME].data.uv_layers[0].data[uvteller].uv = tc2
                      uvteller = uvteller + 1
                      bpy.data.objects[TARGET_NAME].data.uv_layers[0].data[uvteller].uv = tc3
                      uvteller = uvteller + 1
                      bpy.data.objects[TARGET_NAME].data.uv_layers[0].data[uvteller].uv = tc4
                      uvteller = uvteller + 1

      except IOError:
          print('Oh dear. Problems with %s' %(image_texture_filename))

      finally:


 


### TEXTURE END? ##############


        ### Clenaup mesh #######

        # remove verts lacking xyz data
        bpy.ops.object.mode_set(mode='EDIT')
        mesh_ob = bpy.context.object
        me = mesh_ob.data
        bm = bmesh.from_edit_mesh(me)

        verts = [v for v in bm.verts if v.co[0] == 0.0 and v.co[1] == 0.0 and v.co[2] == 0.0]
        bmesh.ops.delete(bm, geom=verts, context="VERTS")
        bmesh.update_edit_mesh(me)

        # remove redundant verts
        bpy.ops.object.mode_set(mode='EDIT')
        mesh_ob = bpy.context.object
        me = mesh_ob.data
        bm = bmesh.from_edit_mesh(me)

        verts = [v for v in bm.verts if len(v.link_faces) == 0]
        bmesh.ops.delete(bm, geom=verts, context="VERTS")
        bmesh.update_edit_mesh(me)

        bpy.ops.object.editmode_toggle()

        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
        bpy.ops.object.mode_set(mode='OBJECT')

        # mesh generation completed, now add camera and caption:

        ##### Add camera ####
        cam = bpy.data.cameras.new('Camera')
        cam.lens = 40
        cam.clip_start = 0.01
        cam_ob = bpy.data.objects.new('Cam-' + os.path.basename(FileAndExt[0]), cam)

        bRoverVec = bRoverVec * 0.1

        mat_loc = mathutils.Matrix.Translation(bRoverVec)
        mat_trans = mathutils.Matrix.Translation((0.0, 0.0, 0.15))

        cam_ob.matrix_world = mat_loc @ mat_trans

        # Create Credit text
        trover = [ 'Spirit', 'Opportunity', 'Curiosity' ]

        if image_texture_filename != None:
          if creation_date.startswith( '\"' ):
              date_object = datetime.strptime(creation_date[1:23], '%Y-%m-%dT%H:%M:%S.%f')
          else:
              date_object = datetime.strptime(creation_date[0:22], '%Y-%m-%dT%H:%M:%S.%f')

          # MSL provides Right Navcam Depth data
          s = list(os.path.basename(image_texture_filename))
          if rover == OPPORTUNITY or rover == SPIRIT:
              if s[23] == 'L' or s[23] == 'l':
                  whichcam = 'Left'
              else:
                  whichcam = 'Right'

          if rover == CURIOSITY:
              if s[1]  == 'L' or s[1] == 'l':
                  whichcam = 'Left'
              else:
                  whichcam = 'Right'

          tagtext = trover[rover-1] + ' ' + whichcam +' Navcam Image at Sol ' + str(sol) + '\n' + str(date_object.strftime('%d %b %Y %H:%M:%S')) + ' UTC\nNASA / JPL-CALTECH / phaseIV'
        else :
          tagtext = 'Texture not found'

        bpy.ops.object.text_add(enter_editmode=True, location = (-0.02, -0.0185, -0.05)) #location = (-0.018, -0.0185, -0.05))
        bpy.ops.font.delete(type='PREVIOUS_WORD')
        bpy.ops.font.text_insert(text=str(tagtext))
        bpy.ops.object.editmode_toggle()

        textSize = 0.001
        text_ob = bpy.context.view_layer.objects.active
        text_ob.scale = [textSize, textSize, textSize]

        tempColl = find_collection(bpy.context, text_ob)
        try:
          theSolCollection.objects.link(text_ob)
          tempColl.objects.unlink(text_ob)
        except:
          print(' ')

        found = None

        for i in range(len(bpy.data.materials)) :
            if bpy.data.materials[i].name == 'White text':
                mat = bpy.data.materials[i]
                found = True
        if not found:
            mat = create_named_material(bpy.context, 'White text')

        text_ob.data.materials.append(mat)
        text_ob.parent = cam_ob

        objloc = Vector(mesh_ob.location)
        rovloc = Vector(bRoverVec)
        distvec = rovloc - objloc

        expoint = obj.matrix_world.to_translation()+Vector((0.0, 0.0, -0.04-distvec.length*0.1))
        look_at(cam_ob, expoint)

        theSolCollection.objects.link(cam_ob)
        bpy.context.scene.camera = cam_ob
        #bpy.context.scene.update()

        print ('Mesh generation complete. Note: you must turn on rendering or preview to see texture.')

    else :
      print ('  ---  Texture not available, skipping...');
      #example : 2N295212876EFFB1DNP1950L0M1


def look_at(obj_camera, point):
    loc_camera = obj_camera.matrix_world.to_translation()

    direction = point - loc_camera

    rot_quat = direction.to_track_quat('-Z', 'Y')
    obj_camera.rotation_euler = rot_quat.to_euler()


def draw(self, context):
    global popup_error

    if(popup_error == 1):
        self.layout.label(text="Unable to retrieve NAVCAM texture image.")
        print("Unable to retrieve NAVCAM texture image.")

    if(popup_error == 2):
        self.layout.label(text="Unable to retrieve NAVCAM depth image.")
        print("Unable to retrieve NAVCAM depth image.")

    if(popup_error == 3):
        self.layout.label(text="Navcam imagename has incorrect length (should be 27 for MER,  36 for MSL).")
        print("Navcam imagename has incorrect length (should be 27 for MER,  36 for MSL).")

    if(popup_error == 4):
        self.layout.label(text="Not a valid Left Navcam imagename: should begin by 1N or 2N for MER, by N for MSL.")
        print("Not a valid Left Navcam imagename: should begin by 1N or 2N for MER, by N for MSL.")


class ROVER_PT_NavcamToolsPanel(bpy.types.Panel):
    bl_label = "Mars Rover Import"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"

    def draw(self, context):
        self.layout.operator("io.navcamdialog_operator")


def menu_func_import(self, context):
    self.layout.operator(NavcamDialogOperator.bl_idname, text="Mars Rover NAVCAM Import")


def register():
    bpy.utils.register_class(NavcamDialogOperator)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.utils.register_class(ROVER_PT_NavcamToolsPanel)


def unregister():
    bpy.utils.unregister_class(NavcamDialogOperator)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.utils.unregister_class(ROVER_PT_NavcamToolsPanel)

def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)



    
if __name__ == "__main__":
    register()
