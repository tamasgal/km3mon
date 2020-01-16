#!/usr/bin/env python
# coding=utf-8
"""
Online Acoustic Monitoring

Usage:
    acoustics.py [options]
    acoustics.py (-h | --help)

Options:
    -d DET_ID       Detector ID
    -n N_DUS        Number of DUs
    -o PLOT_DIR     The directory to save the plot 
    -h --help       Show this screen.

"""
import numpy as np
import matplotlib.pyplot as plt
import time
import os
import matplotlib
from matplotlib import colors
from datetime import datetime
from docopt import docopt
import km3pipe as kp


def diff(first, second):
    second = set(second)
    return [item for item in first if item not in second]


args = docopt(__doc__)

detid = args['-d']
directory = args['-o']
N_DUS = args['-n']
N_DUS = int(N_DUS)

db = kp.db.DBManager()
sds = kp.db.StreamDS()

ACOUSTIC_BEACONS = [12, 14, 16]
N_DOMS = 18
N_ABS=3
DOMS = range(N_DOMS + 1)
DUS = range(1, N_DUS + 1)

TIT = 600 # Time Interval between Trains of acoustic pulses)
SSW = 160 # Signal Security Window (Window size with signal)

check = True
while check:
    
    table = db.run_table(detid)
    minrun = table["RUN"][len(table["RUN"]) - 1]	
    ind, = np.where((table["RUN"] == minrun))
    mintime1 = table['UNIXSTARTTIME'][ind]
    mintime = mintime1.values
    maxrun = table["RUN"][len(table["RUN"]) - 1]
    now = time.time()
    if (now - mintime/1000) < TIT:
        minrun = table["RUN"][len(table["RUN"]) - 1] - 1 
    print(now)

    N_Pulses_Indicator = [] # Matrix indicating how many pulses each piezo reveals
    for du in DUS:
        N_Pulses_Indicator_DU = [] # Array indicating for each DU how many pulses each piezo reveals.
        for ab in ACOUSTIC_BEACONS:
            for dom in DOMS:
                try:
                    domID = db.doms.via_omkey((du, dom), detid).dom_id
                except KeyError:
                    N_Pulses_Indicator_DU.append(-1.5)
                    continue

                try:
                    domID = db.doms.via_omkey((du, dom), detid).dom_id
                    toas_all = sds.toashort(detid = detid, minrun = minrun, maxrun = maxrun, domid = domID, emitterid = ab) 
                
                    QF_abdom = toas_all["QUALITYFACTOR"]
                    UTB_abdom = toas_all["UNIXTIMEBASE"]
                    TOAS_abdom = toas_all["TOA_S"]
                    UTB_abdom = UTB_abdom.values
                    up = np.where(UTB_abdom>(now-TIT))
                    down = np.where(UTB_abdom<(now))
                    intr = np.intersect1d(up,down)
                    UTB_abdom = UTB_abdom[intr]
                    QF_abdom = QF_abdom[intr]                
                    QF_abdom = QF_abdom.values
                    QFlist = QF_abdom.tolist()
                    QFlist.sort(reverse = True)
                    QF_max = max(QF_abdom)
                    QF_max_index = np.where(QF_abdom == QF_max)
                    UTB_signal_min = UTB_abdom[QF_max_index] - SSW/2
                    UTB_signal_max = UTB_abdom[QF_max_index] + SSW/2
                    temp1 = np.where(UTB_abdom > (UTB_signal_min[0]))
                    temp2 = np.where(UTB_abdom < (UTB_signal_max[0]))
                    inter = np.intersect1d(temp1, temp2)
                    inter = inter.tolist()
                    signal_index = inter
                    QF_abdom_index = np.where(QF_abdom)
                    all_data_index = QF_abdom_index[0].tolist()
                    noise_index = diff(all_data_index, signal_index)
                    SIGNAL = QF_abdom[signal_index] 
                    UTB_SIGNAL = UTB_abdom[signal_index]
                    NOISE = QF_abdom[noise_index] 
                    NOISElist = NOISE.tolist()
                    NOISElist.sort(reverse = True)
                    noise_threshold = max(NOISE) 
                    
                    # First filter: 22 greatest
                    Security_Number = 22 # To be sure to take all the pulses
                        
                    SIGNAL = SIGNAL.tolist()
                    SIGNAL_OLD = np.array(SIGNAL)
                    SIGNAL.sort(reverse = True)
                    QF_first = SIGNAL[0:Security_Number]
                    
                    # Second filter: delete duplicates
                    
                    QF_second = np.unique(QF_first)
                    QF_second = QF_second.tolist()
                    QF_second.sort(reverse = True)
                    
                    # Third filter: If there are more than 11 elements I will eliminate the worst
                    
                    if len(QF_second) > 11:
                        QF_second = np.array(QF_second)
                        QF_third = [k for k in QF_second if (np.where(QF_second == k)[0][0] < 11)]
                    else:
                        QF_third = QF_second
                    
                    # Fourth filter: I remove the data if it is below the maximum noise
                    
                    QF_fourth = [k for k in QF_third if k > (noise_threshold + (5*np.std(NOISE)))]
                    
                    # Fifth filter: Check if the clicks are interspersed in the right way
                    
                    Q = []
                    for q in np.arange(len(QF_fourth)):
                        Q.append(np.where(SIGNAL_OLD == QF_fourth[q])[0][0])
                    UTB_fourth = np.array(UTB_SIGNAL.tolist())[Q]
                    UTB_fourth_l = UTB_fourth.tolist()
                    D = []
                    for g in np.arange(len(UTB_fourth_l)):
                        if ((np.mod((UTB_fourth_l[g] - UTB_fourth_l[0]), 5) > 0.5 and np.mod((UTB_fourth_l[g] - UTB_fourth_l[0]), 5) < 4.5) or (np.mod((UTB_fourth_l[g] - UTB_fourth_l[0]), 5)>5)):
                           D.append(g)
                    for d in sorted(D, reverse = True):
                        del QF_fourth[d]  
                    QF_fifth = QF_fourth
                    QF_OK = QF_fifth
                    NUM = len(QF_OK) # Number of pulses
                    print(NUM)
                    
                    if (NUM > 7):
                        N_Pulses_Indicator_DU.append(1.5)
                    elif (NUM < 8 and NUM > 3):
                        N_Pulses_Indicator_DU.append(0.5)
                    elif (NUM < 4 and NUM > 0):
                        N_Pulses_Indicator_DU.append(-0.5)
                    elif (NUM == 0):
                        N_Pulses_Indicator_DU.append(-1.5)

                        
                except (TypeError, ValueError): # TypeError if no data found for a certain piezo, ValueError if there are zero data for a certain piezo
                    N_Pulses_Indicator_DU.append(-1.5)
                    
        N_Pulses_Indicator.append(N_Pulses_Indicator_DU)
        
       
    fig = plt.figure()
    ax = fig.add_subplot(111)
    N_doms = 18
    doms = range(N_doms + 1)
    L = len(doms)
    
    duab = []
    DUs = []
    for du in range(N_DUS):
        duabdu = []
        duab1 = (du+0.9)*np.ones(L)
        duab2 = (du+1)*np.ones(L)
        duab3 = (du+1.1)*np.ones(L)
        duabdu.append(duab1)
        duabdu.append(duab2)
        duabdu.append(duab3)
        duab.append(duabdu)
        DUs.append(np.array(N_Pulses_Indicator[du]))
            
    ind = np.where(DUs[1] < 1000)
    iAB1 = np.where(ind[0] < L)
    iAB2_up = np.where(ind[0] > (L - 1))
    iAB2_down = np.where(ind[0] < 2*L)
    iAB2 = np.intersect1d(iAB2_up, iAB2_down)
    iAB3 = np.where(ind[0] > (2*L - 1))
    
    colorsList = [(0, 0, 0), (1, 0.3, 0), (1, 1, 0), (0.2, 0.9, 0)]
    CustomCmap = matplotlib.colors.ListedColormap(colorsList)
    bounds = [-2, -1, 0, 1, 2]
    norma = colors.BoundaryNorm(bounds, CustomCmap.N)
    for du in range(N_DUS):
        for ab in range(N_ABS):
            color = ax.scatter(duab[du][ab], doms, s = 20, c = DUs[du][iAB1], norm=norma, marker = 's', cmap = CustomCmap);
            color = ax.scatter(duab[du][ab], doms, s = 20, c = DUs[du][iAB2], norm=norma, marker = 's', cmap = CustomCmap);
            color = ax.scatter(duab[du][ab], doms, s = 20, c = DUs[du][iAB3], norm=norma, marker = 's', cmap = CustomCmap);
    
    cbar = plt.colorbar(color)
    cbar.ax.get_yaxis().set_ticks([])
    for j, lab in enumerate(['$0. pings$', '$1-3 pings$', '$4-7 pings$', '$>7. pings$']):
        cbar.ax.text(3.5, (2*j + 1)/8.0, lab, ha = 'center', va = 'center')
    cbar.ax.get_yaxis().labelpad = 18
    
    matplotlib.pyplot.xticks(np.arange(1, N_DUS + 1, step = 1))
    matplotlib.pyplot.yticks(np.arange(0, 19, step = 1))
    matplotlib.pyplot.grid(color = 'k', linestyle = '-', linewidth = 0.2)
    ax.set_xlabel('DUs', fontsize = 18)
    ax.set_ylabel('Floors', fontsize = 18)
    ts = now + 3600
    DATE = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    ax.set_title(r' %.16s Detection of the pings emitted by autonomous beacons' %DATE, fontsize = 10)                  
        
    my_path = os.path.abspath(directory) 
    my_file = 'Online_Acoustic_Monitoring.png'
    
    fig.savefig(os.path.join(my_path, my_file))    
                                        
    print(time.time())
                               
    check = False
    check_time = time.time() - now
    print(check_time)
       
    time.sleep(abs(TIT - check_time))
    check = True  
