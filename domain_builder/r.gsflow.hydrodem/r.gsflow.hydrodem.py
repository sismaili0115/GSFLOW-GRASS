#!/usr/bin/env python
############################################################################
#
# MODULE:       r.gsflow.hydrodem
#
# AUTHOR(S):    Andrew Wickert
#
# PURPOSE:      Builds DEM of elevations for MODFLOW grid as part of GSFLOW,
#               with minimum in-cell elevations chosen for channel cells in 
#               order to maintain a hydrologically correct DEM
#
# COPYRIGHT:    (c) 2016-2017 Andrew Wickert
#
#               This program is free software under the GNU General Public
#               License (>=v2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################
#
# REQUIREMENTS: None (MODFLOW grid can be generated by v.gsflow.grid)
 
# More information
# Started October 2017

#%module
#% description: Creates hydrologically correct MODFLOW DEM from higher-res DEM
#% keyword: vector
#% keyword: stream network
#% keyword: hydrology
#% keyword: GSFLOW
#% keyword: GSFLOW
#%end

#%option G_OPT_R_INPUT
#%  key: dem
#%  label: Input higher-resolution elevation data
#%  required: yes
#%end

#%option G_OPT_V_INPUT
#%  key: grid
#%  label: MODFLOW grid
#%  required: yes
#%end

#%option G_OPT_V_INPUT
#%  key: streams
#%  label: Vector map of stream network (lines)
#%  required: yes
#%end

#%option G_OPT_R_OUTPUT
#%  key: streams_modflow
#%  label: Stream network at MODFLOW grid resolution
#%  required: yes
#%end

#%option G_OPT_R_OUTPUT
#%  key: dem_modflow
#%  label: Hydrologically corrected DEM at MODFLOW grid resolution
#%  required: no
#%end

##################
# IMPORT MODULES #
##################
# PYTHON
import numpy as np
from matplotlib import pyplot as plt
import sys
import warnings
# GRASS
from grass.pygrass.modules.shortcuts import general as g
from grass.pygrass.modules.shortcuts import raster as r
from grass.pygrass.modules.shortcuts import vector as v
from grass.pygrass.modules.shortcuts import miscellaneous as m
from grass.pygrass.gis import region
from grass.pygrass import vector
from grass.script import vector_db_select
from grass.pygrass.vector import Vector, VectorTopo
from grass.pygrass.raster import RasterRow
from grass.pygrass import utils
from grass import script as gscript

###############
# MAIN MODULE #
###############

def main():
    """
    Creates a hydrologically correct MODFLOW grid that inlcudes minimum
    DEM elevations for all stream cells and mean elevations everywhere else
    """
    
    """
    dem = 'DEM'
    grid = 'grid_tmp'
    streams = 'streams_tmp'
    streams_MODFLOW = 'streams_tmp_MODFLOW'
    DEM_MODFLOW = 'DEM_coarse'
    resolution = 500
    """
    
    options, flags = gscript.parser()
    dem = options['dem']
    grid = options['grid']
    streams = options['streams']
    #resolution = float(options['resolution'])
    streams_MODFLOW = options['streams_modflow']
    DEM_MODFLOW = options['dem_modflow']
    
    gscript.use_temp_region()
    
    # Get number of rows and columns
    colNames = np.array(gscript.vector_db_select(grid, layer=1)['columns'])
    colValues = np.array(gscript.vector_db_select(grid, layer=1)['values'].values())
    cats = colValues[:,colNames == 'cat'].astype(int).squeeze()
    rows = colValues[:,colNames == 'row'].astype(int).squeeze()
    cols = colValues[:,colNames == 'col'].astype(int).squeeze()
    nRows = np.max(rows)
    nCols = np.max(cols)
    
    # Set the region
    g.region(vector=grid, rows=nRows, cols=nCols)

    #g.region(raster=dem)
    v.to_rast(input=streams, output=streams_MODFLOW, use='val', value=1.0,
              type='line', overwrite=gscript.overwrite(), quiet=True)
    r.mapcalc(streams_MODFLOW+" = "+streams_MODFLOW+" * DEM", overwrite=True)
    #g.region(res=resolution, quiet=True)
    r.resamp_stats(input=streams_MODFLOW, output=streams_MODFLOW, 
                   method='minimum', overwrite=gscript.overwrite(), quiet=True)
    r.resamp_stats(input=dem, output=DEM_MODFLOW, method='average',
                   overwrite=gscript.overwrite(), quiet=True)
    r.patch(input=streams_MODFLOW+','+DEM_MODFLOW, output=DEM_MODFLOW,
            overwrite=True, quiet=True)

if __name__ == "__main__":
    main()
    
