#! /usr/bin/env python

#####################
# PARSE CONFIG FILE #
#####################

import sys
import os
from ConfigParser import SafeConfigParser # use this in the future

sys.argv.append('../Run/settings_AW.ini')
# Import parsed config file to read in user-specified settings
sys.path.append(os.path.join('..', 'Run'))
from readSettings import Settings
# Set input file
if len(sys.argv) < 2:
    settings_input_file = 'settings.ini'
    print 'Using default input file: ' + settings_input_file
else:
    settings_input_file = sys.argv[1]
    print 'Using specified input file: ' + settings_input_file
try:
    Settings = Settings(settings_input_file)
except:
    sys.exit('Error opening or parsing input file: ' + settings_input_file)

##################
# IMPORT MODULES #
##################
# PYTHON
import numpy as np
# GRASS
from grass.pygrass.modules.shortcuts import general as g
from grass.pygrass.modules.shortcuts import raster as r
from grass.pygrass.modules.shortcuts import vector as v
from grass.pygrass.gis import region
from grass.pygrass import vector # Change to "v"?
from grass.script import vector_db_select
from grass.pygrass.vector import Vector, VectorTopo
from grass.pygrass.raster import RasterRow
from grass.pygrass import utils
from grass import script as gscript
from grass.pygrass.vector.geometry import Point

# Internal variables: set names
DEM_original_import = 'DEM_original_import'   # Raw DEM
DEM                 = 'DEM'                   # DEM after offmap flow removed
DEM_MODFLOW         = 'DEM_MODFLOW'           # DEM for MODFLOW
cellArea_meters2    = 'cellArea_meters2'      # Grid cell size
accumulation        = 'accumulation'          # Flow accumulation
accumulation_onmap  = 'accumulation_onmap'    # Flow accum: no off-map flow
draindir            = 'draindir'              # Drainage direction
streams_all         = 'streams_all'           # Streams on full map
streams_inbasin     = 'streams_inbasin'       # Streams in the study basin
streams_MODFLOW     = 'streams_MODFLOW'       # Streams on MODFLOW grid
basins_all          = 'basins_all'            # All watershed subbasins
basins_inbasin      = 'basins_inbasin'        # Subbasins in the study basin
basin               = 'basin'                 # The full study basin
segments            = 'segments'              # Stream segments
reaches             = 'reaches'               # Stream reaches (for MODFLOW)
MODFLOW_grid        = 'grid'                  # MODFLOW grid vector
slope               = 'slope'                 # Topographic slope
aspect              = 'aspect'                # Topographic aspect
HRUs                = 'HRUs'                  # Hydrologic response units
gravity_reservoirs  = 'gravity_reservoirs'    # Connect HRUs to MODFLOW grid
basin_mask          = 'basin_mask'            # Mask out non-study-basin cells
pour_point          = 'pour_point'            # Outlet pour point
bc_cell             = 'bc_cell'               # Grid cell for MODFLOW b.c.

# Import DEM if required
# And perform the standard starting tasks.
# These take time, so skip if not needed
if Settings.DEM_input != '':
    # Import DEM and set region
    r.in_gdal(input=Settings.DEM_input, output=DEM_original_import, overwrite=True)
    g.region(raster=DEM_original_import)
    # Build flow accumulation with only fully on-map flow
    # Cell areas
    r.cell_area(output=cellArea_meters2, units='m2', overwrite=True)
    # Hydrologic correction
    r.hydrodem(input=DEM_original_import, output=DEM, flags='a', overwrite=True)
    # No offmap flow
    r.watershed(elevation=DEM, flow=cellArea_meters2, accumulation=accumulation, flags='s', overwrite=True)
    r.mapcalc(accumulation_onmap+' = '+accumulation+' * ('+accumulation+' > 0)', overwrite=True)
    r.null(map=accumulation_onmap, setnull=0)
    r.mapcalc('tmp'+' = if(isnull('+accumulation_onmap+'),null(),'+DEM+')', overwrite=True)
    g.copy(raster=('tmp',DEM), overwrite=True)
    # Ensure that null cells are shared
    r.mapcalc(accumulation_onmap+' = if(isnull('+DEM+'),null(),'+accumulation_onmap+')', overwrite=True)
    # Repeat is sometimes needed
    r.mapcalc(DEM+' = if(isnull('+accumulation_onmap+'),null(),'+DEM+')', overwrite=True)
    r.mapcalc(accumulation_onmap+' = if(isnull('+DEM+'),null(),'+accumulation_onmap+')', overwrite=True)


# Set region
g.region(raster=DEM_original_import)

# Build streams and sub-basins
r.stream_extract(elevation=DEM, accumulation=accumulation_onmap, stream_raster=streams_all, stream_vector=streams_all, threshold=Settings.drainage_area_threshold, direction=draindir, d8cut=0, overwrite=True)
r.stream_basins(direction=draindir, stream_rast=streams_all, basins=basins_all, overwrite=True)
r.to_vect(input=basins_all, output=basins_all, type='area', flags='v', overwrite=True)

# Build stream network
v.stream_network(map=streams_all)

# Restrict to a single basin
v.stream_inbasin(input_streams=streams_all, input_basins=basins_all, output_streams=streams_inbasin, output_basin=basins_inbasin, x_outlet=Settings.outlet_point_x, y_outlet=Settings.outlet_point_y, output_pour_point=pour_point, overwrite=True)

# GSFLOW segments: sections of stream that define subbasins
v.gsflow_segments(input=streams_inbasin, output=segments, icalc=Settings.icalc, overwrite=True)

# MODFLOW grid & basin mask (1s where basin exists and 0 where it doesn't)
# Fill nulls in case of ocean
# Any error-related NULL cells will not be part of the basin, and all cells
# should have elevation > 0, so this hopefully will not cause any problems
r.null(map=DEM, null=0)
v.gsflow_grid(basin=basins_inbasin, pour_point=pour_point, raster_input=DEM, dx=Settings.MODFLOW_grid_resolution, dy=Settings.MODFLOW_grid_resolution, output=MODFLOW_grid, mask_output=basin_mask, bc_cell=bc_cell, overwrite=True)
r.null(map=DEM, setnull=0)

# Hydrologically-correct DEM for MODFLOW
r.gsflow_hydrodem(dem=DEM, grid=MODFLOW_grid, streams=streams_all, streams_modflow=streams_MODFLOW, dem_modflow=DEM_MODFLOW, overwrite=True)

# GSFLOW reaches: intersection of segments and grid
v.gsflow_reaches(segment_input=segments, grid_input=MODFLOW_grid, elevation=DEM, output=reaches, overwrite=True)

# GSFLOW HRU parameters
r.slope_aspect(elevation=DEM, slope=slope, aspect=aspect, format='percent', zscale=0.01, overwrite=True)
v.gsflow_hruparams(input=basins_inbasin, elevation=DEM, output=HRUs, slope=slope, aspect=aspect, overwrite=True)

# GSFLOW gravity reservoirs
v.gsflow_gravres(hru_input=HRUs, grid_input=MODFLOW_grid, output=gravity_reservoirs, overwrite=True)

# Export DEM with MODFLOW resolution
# Also export basin mask -- 1s where basin exists and 0 where it doesn't
# And make sure it is in an appropriate folder
if os.getcwd() != Settings.GIS_output_rootdir:
    try:
        os.makedirs(Settings.GIS_output_rootdir)
    except:
        pass
os.chdir(Settings.GIS_output_rootdir)
g.region(raster=DEM_MODFLOW)
r.out_ascii(input=DEM_MODFLOW, output='DEM.asc', null_value=0, overwrite=True)
r.out_ascii(input=basin_mask, output=basin_mask+'.asc', null_value=0, overwrite=True)
g.region(raster=DEM)

# Export tables and discharge point
v.gsflow_export(reaches_input=reaches,
                segments_input=segments,
                gravres_input=gravity_reservoirs,
                hru_input=HRUs,
                pour_point_input=pour_point,
                bc_cell_input=bc_cell,
                reaches_output=reaches,
                segments_output=segments,
                gravres_output=gravity_reservoirs,
                hru_output=HRUs,
                pour_point_boundary_output=pour_point,
                overwrite=True)
                
# Generate a vector of the full basin area
# "value" column is empty
v.dissolve(input=basins_inbasin, output=basin, column='label', overwrite=True)

# Export shapefiles of all vector files
try:
    os.mkdir('shapefiles')
except:
    pass
os.chdir('shapefiles')
for _vector_file in [HRUs, gravity_reservoirs, MODFLOW_grid, basin]:
    v.out_ogr(input=_vector_file, output=_vector_file, type='area', quiet=True, overwrite=True)
for _vector_file in [segments, reaches]:
    v.out_ogr(input=_vector_file, output=_vector_file, type='line', quiet=True, overwrite=True)
for _vector_file in [pour_point, bc_cell]:
    v.out_ogr(input=_vector_file, output=_vector_file, type='point', quiet=True, overwrite=True)
os.chdir('..')
os.chdir('..')

print ""
print "Done."
print ""