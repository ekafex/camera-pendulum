# -*- coding: utf-8 -*-
"""
Created on Wed Dec 24 17:52:53 2025

@author: EK
"""

import numpy as np
import matplotlib.pyplot as plt

#===============================================
def hist_dt(paths,labels,colors,save=0,fname='frame_dist',xy_limits={'xmin':5,'xmax':45,'ymin':1e-9,'ymax':1e-5}):
    fig1=plt.figure(num=1,figsize=(7,6),dpi=100)
    ax1=fig1.add_axes([0.11, 0.09, 0.86, 0.88])
    for direct in ['top','left','bottom','right']:
        ax1.spines[direct].set_linewidth(2)
    key1={'which':'major','length':13,'width':2.2,'direction':'in','right':True,'top':True}
    key2={'which':'minor','length': 6,'width': 2.2,'direction':'in','right':True,'top':True}
    ax1.tick_params(axis=u'both',**key1)
    ax1.tick_params(axis=u'both',**key2)
    font = {'size' : 13}
    plt.rc('font', **font)
    for i,p in enumerate(paths):
        iFrame,read_ok,t_before_read_ns,t_after_read_ns = np.loadtxt(p+'/timestamps.csv',delimiter=',',unpack=True)
        dt = t_after_read_ns - t_before_read_ns
        hist,bins = np.histogram(dt,bins=90,density=True)
        ax1.plot(1e-6*bins[:-1],hist,ls='-',color=colors[i],lw=3,ds='steps-mid',label=labels[i])
    ax1.legend(loc=0,frameon=False,fontsize=15)
    ax1.set_xlabel(r'$\Delta t\,[ms]$',fontsize=15)
    ax1.set_ylabel(r'$f(\Delta t)$',fontsize=15)
    ax1.set_yscale('log')
    ax1.set_xlim(left=xy_limits['xmin'],right=xy_limits['xmax'])
    ax1.set_ylim(bottom=xy_limits['ymin'], top=xy_limits['ymax'])
    if save:
        fig1.savefig(f'runs/all_figs/pdf/{fname}.pdf', format='pdf')
        fig1.savefig(f'runs/all_figs/png/{fname}.png', format='png')

#===============================================
#===============================================
#===============================================

# paths = ['runs/timing_720p_req60_600s_v1',
#          'runs/timing_720p_req60_600s_v2_stress_cpu_load_testA',
#          'runs/timing_720p_req60_600s_v2_stress_cpu+IO_load_testB']

# labels=['No load','CPU load','CPU + IO load']
# colors=['k','r','c']
# xy_limits={'xmin':10,'xmax':40,'ymin':1e-9,'ymax':1e-5}
# hist_dt(paths, labels, colors, save=1, fname='frame_dist',xy_limits=xy_limits)

#===============================================
# paths = ['runs/performance/EnergySaving_600s','runs/performance/Performance_600s']
# labels=['Energy Saving','Performance']
# colors=['k','r','c']
# xy_limits={'xmin':15,'xmax':30,'ymin':1e-9,'ymax':1e-5}

# hist_dt(paths, labels, colors, save=1,fname='Performance_Mode',xy_limits=xy_limits)

#===============================================

# paths = ['runs/Normal_OS_scheduling_600',
#          'runs/taskset_OS_scheduling_600',
#          'runs/chrt_taskset_OS_scheduling_600',
#          'runs/chrt_OS_scheduling_600']

# labels=['Normal','taskset','chrt+taskset','chrt']
# colors=['k','r','c','tab:brown']
# xy_limits={'xmin':17,'xmax':25,'ymin':1e-9,'ymax':1e-5}
# hist_dt(paths, labels, colors, save=0, fname='schedule',xy_limits=xy_limits)


#===============================================

p = 'runs/Normal_OS_scheduling_600'
iFrame,read_ok,t_before_read_ns,t_after_read_ns = np.loadtxt(p+'/timestamps.csv',delimiter=',',unpack=True)
dt = t_after_read_ns - t_before_read_ns
dt1 = np.diff(t_before_read_ns)
dt2 = np.diff(t_after_read_ns)
hist,bins = np.histogram(dt,bins=90,density=True)
hist1,bins1 = np.histogram(dt1,bins=90,density=True)
hist2,bins2 = np.histogram(dt2,bins=90,density=True)

plt.plot(1e-6*bins[:-1],hist,'-k',lw=2,ds='steps-mid')
plt.plot(1e-6*bins1[:-1],hist1,'-r',lw=2,ds='steps-mid')
plt.plot(1e-6*bins2[:-1],hist2,'-c',lw=2,ds='steps-mid')




# if __name__ == "__main__":
#     # hist_dt(save=0)
#     # plt.plot(iFrame2, 1e-13*t_before_read_ns2,'-k',lw=2)
#     # plt.plot(iFrame2, 1e-13*t_after_read_ns2,'-r',lw=2)
#     plt.plot(1e-13*t_before_read_ns2,1e-13*t_after_read_ns2,'-k',lw=2)
#     # plt.xscale('log')
#     # plt.yscale('log')


