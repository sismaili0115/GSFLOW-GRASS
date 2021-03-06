#! /usr/bin/env python

# -*- coding: utf-8 -*-
"""
Created on Sun Oct 29 15:26:24 2017

@author: gcng
"""

# plot_gsflow_csv.m
# 
# List of StatVarNames: see Table 12 of GSFLOW manual and 
#  create_table_gsflowcsv.m

import sys
import platform
import numpy as np
from matplotlib import pyplot as plt
import pandas as pd
import datetime as dt
import matplotlib.dates as mdates
import GSFLOWcsvTable as gvar  # all variable names, units, and descriptions
plt.ion()

if platform.system() == 'Linux':
    slashstr = '/'
else:
    slashstr = '\\'

# add path containing readSettings.py
sys.path.append('..' + slashstr + 'Run')

## Read in user-specified settings
#from readSettings import Settings
## Set input file
#if len(sys.argv) < 2:
#    settings_input_file = 'settings.ini'
#    print 'Using default input file: ' + settings_input_file
#else:
#    settings_input_file = sys.argv[1]
#    print 'Using specified input file: ' + settings_input_file
#Settings = Settings(settings_input_file)

#%% *** SET THE FOLLOWING *****************************************************
 
# *** enter variables to plot (see list in gsflow_csv_table.py):
PlotVar = []
PlotVar.append('basinppt')
#PlotVar.append('basinactet')

#PlotVar.append('basinstrmflow')
#PlotVar.append('uzf_recharge')
PlotVar.append('basinsroff')
#PlotVar.append('gwflow2strms')
#PlotVar.append('basininterflow')
#PlotVar.append('streambed_loss')


# *** save figure to this file
savefigfile = 'fig.png'

#%% *** CHANGE FILE NAMES IF NEEDED *******************************************
## (default is to use entries from Settings File) 
#gsflow_csv_fil = Settings.PRMSoutput_dir + slashstr + 'gsflow.csv'  # gsflow time series data
#plot_title = Settings.PROJ_CODE
#
##  *** CHANGE BASIN AREA AS NEEDED (SEE prms.out FILE FOR AREA IN [acres]) ***
## (default is to use entries from Settings File) 
#HRUfil = Settings.GISinput_dir + slashstr + 'HRUs.txt'
#HRUdata = pd.read_csv(HRUfil)
#HRUarea = HRUdata['hru_area']  # [acre]
#basin_area = sum(HRUarea) * 4046.85642  # acre -> m2

"""

# - Shullcas
# run script with F5
plot_title = 'Shullcas'
gsflow_csv_fil = '/media/gcng/STORAGE3A/ANDY/GSFLOW/Shullcas' + '/outputs/PRMS_GSFLOW/gsflow.csv'  # gsflow time series data
#gsflow_csv_fil = '/home/gcng/workspace/ProjectFiles/GSFLOW-GRASS_ms/examples4ms/Shullcas' + '/outputs/PRMS_GSFLOW/gsflow.csv'  # gsflow time series data
gsflow_csv_fil = '/home/awickert/GSFLOW/Shullcas' + '/outputs/PRMS_GSFLOW/gsflow.csv'  # gsflow time series data
basin_area = 39873.97 * 4046.85642  # acre -> m2
PlotVar = []
PlotVar.append('basinppt')
PlotVar.append('basinstrmflow')
pTimeLastNDays = 365*2
#figsize0 = (8*3,6) # 3x as wide as default (8W,6H)
savefigfile = 'Shullcas_timeseries'
clr = ['b', 'k', 'r', 'g']
#colspan_i = 1
#rowspan_i = 1 
multi = 3
plot_title_ltr = 'Streamflow and Precipitation'


## - Santa Rosa
## run script with F5
plot_title = 'Santa Rosa'
gsflow_csv_fil = '/home/awickert/GSFLOW/SantaRosa' + '/outputs/PRMS_GSFLOW/gsflow.csv'  # gsflow time series data
basin_area = 3078.39 * 4046.85642  # acre -> m2
PlotVar = []
PlotVar.append('basinppt')
PlotVar.append('basinsroff')
#PlotVar.append('basinstrmflow') # not for paper, just to see when to print streamflow
pTimeLastNDays = 365*1
#figsize0 = (8*2,6)
savefigfile = 'SR_timeseries'
clr = ['b', 'r', 'k']
plot_title_ltr = 'Surface Runoff and Precipitation'
multi=2
"""

## - Cannon River
## run script with F5
plot_title = 'Cannon River'
gsflow_csv_fil = '/home/awickert/GSFLOW/CannonRiver_2layer' + '/outputs/PRMS_GSFLOW/gsflow.csv'  # gsflow time series data
basin_area = 3783E6 #3078.39 * 4046.85642  # acre -> m2 # WRONG!!!!!!!!
PlotVar = []
PlotVar.append('basinppt')
PlotVar.append('basinstrmflow')
#PlotVar.append('basinstrmflow') # not for paper, just to see when to print streamflow
pTimeLastNDays = 365*3
#figsize0 = (8*2,6)
savefigfile = 'C_timeseries'
clr = ['b', 'k', 'r', 'g']
plot_title_ltr = 'Streamflow and Precipitation'
multi=2


# font sizes
mult = 1
FS_lab = 10 * mult * 2/3.
FS_cvtick = 8 * mult * 2/3.
FS_xylab = 10 * mult * 2/3.
FS_clab = 8 * mult * 2/3.
FS_ti = 10 * mult * 2/3.

figsize0 = (2.5*mult*multi,2.5*mult)
plot_pos = (0,0)
tight_layout = True


#%%

## make sure basinppt and basinacet are listed last, because of twin y-axis
#PlotVar0 = PlotVar[:]
#ctr = 1
#ctr_end = len(PlotVar)
#for ii in range(len(PlotVar)):
#    if (PlotVar[ii] == 'basinppt') or (PlotVar[ii] == 'basinactet'):
#        PlotVar0[ctr_end-1] = PlotVar[ii]
#        ctr_end = ctr_end - 1
#    else:
#        PlotVar0[ctr-1] = PlotVar[ii]
#        ctr = ctr + 1
#PlotVar = PlotVar0[:]

descr = []
unit_prev = []
for jj in range(len(PlotVar)):
    for ii in range(len(gvar.varname)):
        if gvar.varname[ii] == PlotVar[jj]:
            unit = gvar.unit[ii]
            descr.append(gvar.descr[ii])
            if (jj > 0) and (unit != unit_prev):
                    print "Error! Plot variables do not have same units.  Exiting..."
                    sys.exit()
            unit_prev = unit
            break
    

## Read in data

# header{1,NVars}: variable name
# data{NVars}: all data 
data = pd.read_csv(gsflow_csv_fil)
data = data[-pTimeLastNDays:]
    
dateList = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in data['Date']]

# - plot data
#fig, ax1 = plt.subplots(figsize=(14,5))
#fig = plt.figure(figsize=figsize0)
nrows = 1
ncols = 1
fig = plt.figure(1, figsize=figsize0)
#ax1 = plt.subplot2grid((nrows, ncols), plot_pos, colspan=colspan_i, rowspan=rowspan_i)
ax1 = fig.add_subplot(1,1,1)
if tight_layout:
    plt.tight_layout()
#fig, ax1 = plt.subplots(212)
ax2 = ax1.twinx()
if tight_layout:
    plt.tight_layout()

# convert volume units [m^3] to length [mm]
conv = 1.
if unit[0:3] == 'm^3':
    conv = 1. / basin_area * 1000.
    unit0 = 'mm' 
    if len(unit) > 3:
        unit0 = unit0 + unit[3:]
    unit = unit0[:]
    
#plt.close("all")
PlotVarLeg = PlotVar 
for ii in range(len(PlotVar)):
    
    if (PlotVar[ii] == 'basinppt') or (PlotVar[ii] == 'basinactet'):
        ln0 = ax2.plot(dateList, conv*data[PlotVar[ii]], clr[ii], linewidth=2, alpha=.5 )
        ax2.set_ylabel('Precipitation ' + unit, fontsize=FS_xylab)
        PlotVarLeg[ii] = 'Precipitation'
    else:
        ln0 = ax1.plot(dateList, conv*data[PlotVar[ii]], clr[ii], linewidth=3, alpha=1.0) 
        if PlotVar[ii] == 'basinstrmflow':
            ti = 'Streamflow'
        elif PlotVar[ii] == 'basinsroff':
            ti = 'Runoff'
        PlotVarLeg[ii] = ti
        ax1.set_ylabel(ti + ' ' + unit, fontsize=FS_xylab)


    if ii == 0:
        lns = ln0
    else:
        lns = lns + ln0
     
#    plt.plot(range(len(data)), data[PlotVar[ii]])
#    plt.show
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%y'))
#    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gcf().autofmt_xdate()    

# Plus data for the Cannon
cd = pd.read_csv('/home/awickert/Dropbox/Papers/Submitted/GSFLOW-GRASS/figures/inprogress/hydro_data_39004002_1909-07-01_2018-04-21.csv', infer_datetime_format=True, parse_dates=True, index_col=1)
idx = (cd.index > pd.datetime(1940, 11, 6)) * (cd.index < pd.datetime(1943, 11, 5))
ln0 = ax1.plot(cd['Discharge (cfs)'][idx]/35.3146667*(3600*24*1000/3723E6), '-', color='0.7', linewidth=2)
lns = lns + ln0
PlotVar += ['Welch, MN gauge']
print np.mean(cd['Discharge (cfs)'][idx])/35.3146667*(3600*24*1000/3723E6)
print np.std(cd['Discharge (cfs)'][idx])/35.3146667*(3600*24*1000/3723E6)
# From model
print np.mean(conv*data['basinstrmflow'])
print np.std(conv*data['basinstrmflow'])



#ax1.set_xlim(dateList[-pTimeLastNDays-1],dateList[-1])
ax1.set_xlim(dateList[0],dateList[-1])
#ax1.set_xlim(dateList[-365*2-1],dateList[-1])
ax1.legend(lns, PlotVarLeg, loc=0, fontsize=FS_xylab)
ax1.tick_params(axis="both", which="major", labelsize=FS_cvtick)
ax2.tick_params(axis="both", which="major", labelsize=FS_cvtick)

#ax2.set_ylim(ax1.get_ylim()[0], np.round(conv*np.max(data['basinppt'])*1.1/10.)*10. )
    
#plt.legend(PlotVar)
#plt.title(plot_title, fontsize=FS_ti, fontweight='bold')
plt.title(plot_title_ltr, fontsize=FS_ti)
#plt.tight_layout()
#ax1.set_aspect('equal', 'datalim')
#ax2.set_aspect('equal', 'datalim')

plt.savefig(savefigfile+'.png', dpi = 100)
plt.savefig(savefigfile+'.svg', dpi = 100)

plt.show()

print '\n-------------------'
print 'Plotting: '
for ii in range(len(PlotVar)):
    print '- ' + PlotVar[ii] + ' (' + unit + '): ' + descr[ii]
print '-------------------\n'


