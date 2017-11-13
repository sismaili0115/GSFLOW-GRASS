#!/usr/bin/env python
############################################################################
#
# MODULE:       v.gsflow.grid
#
# AUTHOR(S):    Andrew Wickert
#
# PURPOSE:      Builds grid for the MODFLOW component of GSFLOW
#
# COPYRIGHT:    (c) 2016-2017 Andrew Wickert
#
#               This program is free software under the GNU General Public
#               License (>=v2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################
#
# REQUIREMENTS:
#      -  uses inputs from r.stream.extract
 
# More information
# Started December 2016

#%module
#% description: Builds grid for the MODFLOW component of GSFLOW
#% keyword: vector
#% keyword: stream network
#% keyword: hydrology
#% keyword: GSFLOW
#%end

#%option G_OPT_V_INPUT
#%  key: basin
#%  label: Study basin, over which to build a MODFLOW grid
#%  required: yes
#%end

#%option G_OPT_V_INPUT
#%  key: pour_point
#%  label: Pour point, to which row and col (MODFLOW) will be added
#%  required: yes
#%end

#%option G_OPT_R_INPUT
#%  key: raster_input
#%  label: Raster to be resampled to grid resolution
#%  required: no
#%end

#%option
#%  key: dx
#%  label: Cell size suggestion (x / E / zonal), map units: rounds to DEM
#%  required: yes
#%end

#%option
#%  key: dy
#%  label: Cell size suggestion (y / N / meridional), map units: rounds to DEM
#%  required: yes
#%end

#%option G_OPT_V_OUTPUT
#%  key: output
#%  label: MODFLOW grid
#%  required: yes
#%end

#%option G_OPT_R_OUTPUT
#%  key: mask_output
#%  label: Raster basin mask: inside (1) or outside (0) the watershed?
#%  required: no
#%end

#%option G_OPT_V_OUTPUT
#%  key: bc_cell
#%  label: Constant-head boundary condition cell
#%  required: yes
#%end

##################
# IMPORT MODULES #
##################
# PYTHON
import numpy as np
# GRASS
from grass.pygrass.modules.shortcuts import general as g
from grass.pygrass.modules.shortcuts import raster as r
from grass.pygrass.modules.shortcuts import vector as v
from grass.pygrass.modules.shortcuts import miscellaneous as m
from grass.pygrass.gis import region
from grass.pygrass import vector # Change to "v"?
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
    Builds a grid for the MODFLOW component of the USGS hydrologic model,
    GSFLOW.
    """
    
    options, flags = gscript.parser()
    basin = options['basin']
    pp = options['pour_point']
    raster_input = options['raster_input']
    dx = options['dx']
    dy = options['dy']
    grid = options['output']
    mask = options['mask_output']
    bc_cell = options['bc_cell']
    # basin='basins_tmp_onebasin'; pp='pp_tmp'; raster_input='DEM'; raster_output='DEM_coarse'; dx=dy='500'; grid='grid_tmp'; mask='mask_tmp'
    
    """
    # Fatal if raster input and output are not both set
    _lena0 = (len(raster_input) == 0)
    _lenb0 = (len(raster_output) == 0)
    if _lena0 + _lenb0 == 1:
        grass.fatal("You must set both raster input and output, or neither.")
    """
    
    # Fatal if bc_cell set but mask and grid are false
    if bc_cell != '':
        if (mask == '') or (pp == ''):
            grass.fatal('Mask and pour point must be set to define b.c. cell')
        
    # Create grid -- overlaps DEM, one cell of padding
    gscript.use_temp_region()
    reg = gscript.region()
    reg_grid_edges_sn = np.linspace(reg['s'], reg['n'], reg['rows'])
    reg_grid_edges_we = np.linspace(reg['w'], reg['e'], reg['cols'])
    g.region(vector=basin, ewres=dx, nsres=dy)
    regnew = gscript.region()
    # Use a grid ratio -- don't match exactly the desired MODFLOW resolution
    grid_ratio_ns = np.round(regnew['nsres']/reg['nsres'])
    grid_ratio_ew = np.round(regnew['ewres']/reg['ewres'])
    # Get S, W, and then move the unit number of grid cells over to get N and E
    # and include 3 cells of padding around the whole watershed
    _s_dist = np.abs(reg_grid_edges_sn - (regnew['s'] - 3.*regnew['nsres']) )
    _s_idx = np.where(_s_dist == np.min(_s_dist))[0][0]
    _s = float(reg_grid_edges_sn[_s_idx])
    _n_grid = np.arange(_s, reg['n'] + 3*grid_ratio_ns*reg['nsres'], grid_ratio_ns*reg['nsres'])
    _n_dist = np.abs(_n_grid - (regnew['n'] + 3.*regnew['nsres']))
    _n_idx = np.where(_n_dist == np.min(_n_dist))[0][0]
    _n = float(_n_grid[_n_idx])
    _w_dist = np.abs(reg_grid_edges_we - (regnew['w'] - 3.*regnew['ewres']))
    _w_idx = np.where(_w_dist == np.min(_w_dist))[0][0]
    _w = float(reg_grid_edges_we[_w_idx])
    _e_grid = np.arange(_w, reg['e'] + 3*grid_ratio_ew*reg['ewres'], grid_ratio_ew*reg['ewres'])
    _e_dist = np.abs(_e_grid - (regnew['e'] + 3.*regnew['ewres']))
    _e_idx = np.where(_e_dist == np.min(_e_dist))[0][0]
    _e = float(_e_grid[_e_idx])
    # Finally make the region
    g.region(w=str(_w), e=str(_e), s=str(_s), n=str(_n), nsres=str(grid_ratio_ns*reg['nsres']), ewres=str(grid_ratio_ew*reg['ewres']))
    # And then make the grid
    v.mkgrid(map=grid, overwrite=gscript.overwrite())

    # Cell numbers (row, column, continuous ID)
    v.db_addcolumn(map=grid, columns='id int', quiet=True)
    colNames = np.array(gscript.vector_db_select(grid, layer=1)['columns'])
    colValues = np.array(gscript.vector_db_select(grid, layer=1)['values'].values())
    cats = colValues[:,colNames == 'cat'].astype(int).squeeze()
    rows = colValues[:,colNames == 'row'].astype(int).squeeze()
    cols = colValues[:,colNames == 'col'].astype(int).squeeze()
    nrows = np.max(rows)
    ncols = np.max(cols)
    cats = np.ravel([cats])
    _id = np.ravel([ncols * (rows - 1) + cols])
    _id_cat = []
    for i in range(len(_id)):
        _id_cat.append( (_id[i], cats[i]) )
    gridTopo = VectorTopo(grid)
    gridTopo.open('rw')
    cur = gridTopo.table.conn.cursor()
    cur.executemany("update "+grid+" set id=? where cat=?", _id_cat)
    gridTopo.table.conn.commit()
    gridTopo.close()

    # Cell area
    v.db_addcolumn(map=grid, columns='area_m2', quiet=True)
    v.to_db(map=grid, option='area', units='meters', columns='area_m2', quiet=True)

    # Basin mask
    if len(mask) > 0:
        # Fine resolution region:
        g.region(n=reg['n'], s=reg['s'], w=reg['w'], e=reg['e'], nsres=reg['nsres'], ewres=reg['ewres'])
        # Rasterize basin
        v.to_rast(input=basin, output=mask, use='val', value=1, overwrite=gscript.overwrite(), quiet=True)
        # Coarse resolution region:
        g.region(w=str(_w), e=str(_e), s=str(_s), n=str(_n), nsres=str(grid_ratio_ns*reg['nsres']), ewres=str(grid_ratio_ew*reg['ewres']))
        r.resamp_stats(input=mask, output=mask, method='sum', overwrite=True, quiet=True)
        r.mapcalc(mask+' = '+mask+' > 0', overwrite=True, quiet=True)
        # Add mask location (1 vs 0) in the MODFLOW grid
        v.db_addcolumn(map=grid, columns='basinmask', quiet=True)
        v.what_rast(map=grid, type=centroid, raster=mask, column='basinmask')

    """
    # Resampled raster
    if len(raster_output) > 0:
        r.resamp_stats(input=raster_input, output=raster_output, method='average', overwrite=gscript.overwrite(), quiet=True)
    """

    # Pour point
    if len(pp) > 0:
        v.db_addcolumn(map=pp, columns=('row integer','col integer'), quiet=True)
        v.build(map=pp, quiet=True)
        v.what_vect(map=pp, query_map=grid, column='row', query_column='row', quiet=True)
        v.what_vect(map=pp, query_map=grid, column='col', query_column='col', quiet=True)

    # Next point downstream of the pour point
    # Requires pp (always) and mask (sometimes)
    # Dependency set above w/ grass.fatal
    if len(bc_cell) > 0:
        ########## NEED TO USE TRUE TEMPORARY FILE ##########
        # May not work with dx != dy!
        v.to_rast(input=pp, output='tmp', use='val', value=1, overwrite=True)
        r.buffer(input='tmp', output='tmp', distances=float(dx)*1.5, overwrite=True)
        r.mapcalc('tmp = (tmp == 2) * '+raster_input, overwrite=True)
        #r.mapcalc('tmp = if(isnull('+raster_input+',0,(tmp == 2)))', overwrite=True)
        #g.region(rast='tmp')
        #r.null(map=raster_input,
        r.drain(input=raster_input, start_points=pp, output='tmp2', overwrite=True)
        r.mapcalc('tmp = tmp2 * tmp', overwrite=True)
        r.null(map='tmp', setnull=0)
        r.to_vect(input='tmp', output=bc_cell, type='point', column='z',
                  overwrite=gscript.overwrite(), quiet=True)
        v.db_addcolumn(map=bc_cell, columns=('row integer','col integer'), quiet=True)
        v.build(map=bc_cell, quiet=True)
        v.what_vect(map=bc_cell, query_map=grid, column='row', \
                    query_column='row', quiet=True)
        v.what_vect(map=bc_cell, query_map=grid, column='col', \
                    query_column='col', quiet=True)
        
        # Find out if this is diagonal: finite difference works only N-S, W-E
        colNames = np.array(gscript.vector_db_select(pp, layer=1)['columns'])
        colValues = np.array(gscript.vector_db_select(pp, layer=1)['values'].values())
        pp_row = colValues[:,colNames == 'row'].astype(int).squeeze()[0]
        pp_col = colValues[:,colNames == 'col'].astype(int).squeeze()[0]
        colNames = np.array(gscript.vector_db_select(bc_cell, layer=1)['columns'])
        colValues = np.array(gscript.vector_db_select(bc_cell, layer=1)['values'].values())
        bc_row = colValues[:,colNames == 'row'].astype(int).squeeze()[0]
        bc_col = colValues[:,colNames == 'col'].astype(int).squeeze()[0]
        # Check if diagonal
        if (bc_row != pp_row) and (bc_col != pp_col):
            # If not diagonal, two possible locations that are adjacent
            # to the pour point
            x1, y1 = bc_col, pp_row
            x2, y2 = pp_col, bc_row
            # Check if either of these is covered by the basin mask
            _ismask_1 = grass.vector_db_select(grid, layer=1, where='(row == '+pp_row+') AND (col =='+pp_col+')', column='basinmask')
            ...
            
            # If both covered by mask, error
            if 
                grass.fatal
            # Otherwise, those that keep those that are not covered by basin
            # mask and set ...
            # ... wait, do we want the point that touches as few interior
            # cells as possible?
            # maybe just try setting both and seeing what happens for now!
            else:
                # Build tool to handle multiple b.c. cells?
                bcvect = vector.Vector(bc_cell)
                bcvect.open('a'?
                if not _ismask_1:
                    ... see below key on how to build 
                if not _ismask_2:
                    ...
            
            # From pour points; use as template for adding more points here
            tmp.open('w', tab_name='tmp', tab_cols=_cols)
            point0 = Point(x_outlet,y_outlet)
            tmp.write(point0, cat=1, attrs=(str(x_outlet), str(y_outlet), 0), )
            tmp.table.conn.commit()
            tmp.build()
            tmp.close()


        
    g.region(n=reg['n'], s=reg['s'], w=reg['w'], e=reg['e'], nsres=reg['nsres'], ewres=reg['ewres'])


if __name__ == "__main__":
    main()
