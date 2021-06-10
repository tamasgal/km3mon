#!/usr/bin/env python
# coding=utf-8
"""
Online Acoustic Monitoring

Usage:
    acoustics.py [options]
    acoustics.py (-h | --help)

Options:
    -d DET_ID       Detector ID.
    -o PLOT_DIR     The directory to save the plot [default: /plots].
    -h --help       Show this screen.

"""
from datetime import datetime
import os
import time
import http
import ssl

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
import numpy as np
import km3db
import km3pipe as kp
from docopt import docopt


def diff(first, second):
    second = set(second)
    return [item for item in first if item not in second]


def duplicates(lst, item):
    return [i for i, x in enumerate(lst) if x == item]


args = docopt(__doc__)

sds = km3db.StreamDS(container="pd")
                    
try:
    detid = int(args['-d'])
except ValueError:
    detid = (args['-d'])
if type(detid)==int:
    detid = km3db.tools.todetoid(detid)

directory = args['-o']

ACOUSTIC_BEACONS = [0, 0, 0]

N_DOMS = 18
N_ABS = 3
DOMS = range(N_DOMS + 1)
DUS = kp.hardware.Detector(det_id=detid).dus
DUS_cycle = list(np.arange(max(DUS)) + 1)

TIT = 600  # Time Interval between Trains of acoustic pulses)
SSW = 160  # Signal Security Window (Window size with signal)

clbmap = km3db.CLBMap(detid)

check = True
while check:

    minrun = None
    while minrun is None:
        try:
            table = sds.runs(detid=detid)
            minrun = table["RUN"][len(table["RUN"]) - 1]
            ind, = np.where((table["RUN"] == minrun))
            mintime1 = table['UNIXSTARTTIME'][ind]
            mintime = mintime1.values
            maxrun = table["RUN"][len(table["RUN"]) - 1]
            now = time.time()
            now = now - TIT
            if (now - mintime / 1000) < TIT:
                minrun = table["RUN"][len(table["RUN"]) - 1] - 1
            print(now)
        except:
            pass
        
    N_Pulses_Indicator = [
    ]  # Matrix indicating how many pulses each piezo reveals
    for du in DUS_cycle:
        N_Pulses_Indicator_DU = [
        ]  # Array indicating for each DU how many pulses each piezo reveals.
        for dom in DOMS:
            UTB_MIN = []
            QF_MAX = []

            n = -1            
            for ab in ACOUSTIC_BEACONS:
                n = n + 1
                try:
                    domID = clbmap.omkeys[(du, dom)].dom_id
                    
                    AcBe = sds.toashort(detid=detid,
                        minrun=minrun,
                        domid=domID,
                        maxrun=maxrun)      
                
                    ACOUSTIC_BEACONS_TEMP = np.unique(AcBe["EMITTERID"]).tolist()
                    if np.size(ACOUSTIC_BEACONS_TEMP) < 3:
                        while np.size(ACOUSTIC_BEACONS_TEMP) < 3:
                            ACOUSTIC_BEACONS_TEMP.append(0)
                    ACOUSTIC_BEACONS_TEMP_2 = np.sort(np.abs(ACOUSTIC_BEACONS_TEMP))
                    m = np.where(np.abs(ACOUSTIC_BEACONS_TEMP) == ACOUSTIC_BEACONS_TEMP_2[n])[0][0]
                    ab = ACOUSTIC_BEACONS_TEMP[m]
                    print(ab)
                    
                except (KeyError, AttributeError, TypeError):
                    N_Pulses_Indicator_DU.append(-1.5)
                    continue
                
                try:
                    toas_all = sds.toashort(detid=detid,
                                            minrun=minrun,
                                            maxrun=maxrun,
                                            domid=domID,
                                            emitterid=ab)
                    QF_abdom = toas_all["QUALITYFACTOR"]
                    UTB_abdom = toas_all["UNIXTIMEBASE"]
                    TOAS_abdom = toas_all["TOA_S"]
                    UTB_abdom = UTB_abdom.values
                    up = np.where(UTB_abdom > (now - TIT))
                    down = np.where(UTB_abdom < (now))
                    intr = np.intersect1d(up, down)
                    UTB_abdom = UTB_abdom[intr]
                    QF_abdom = QF_abdom[intr]
                    QF_abdom = QF_abdom.values
                    QFlist = QF_abdom.tolist()
                    QFlist.sort(reverse=True)
                    QF_max = max(QF_abdom)
                    QF_max_index = np.where(QF_abdom == QF_max)
                    UTB_signal_min = UTB_abdom[QF_max_index[0][0]] - SSW / 2
                    UTB_signal_max = UTB_abdom[QF_max_index[0][0]] + SSW / 2
                    temp1 = np.where(UTB_abdom > (UTB_signal_min))
                    temp2 = np.where(UTB_abdom < (UTB_signal_max))
                    inter = np.intersect1d(temp1, temp2)
                    inter = inter.tolist()
                    signal_index = inter

                    # Define the signal index if the the pings are splitted in two parts inside the window

                    if UTB_signal_min < (now - TIT):
                        temp1 = np.where(UTB_abdom > (now - TIT))
                        temp2 = np.where(UTB_abdom < (UTB_signal_max))
                        inter1 = np.intersect1d(temp1, temp2)
                        inter1 = inter1.tolist()
                        temp11 = np.where(UTB_abdom < (now))
                        temp22 = np.where(UTB_abdom > (now - SSW / 2))
                        inter2 = np.intersect1d(temp11, temp22)
                        inter2 = inter2.tolist()
                        inter = np.union1d(inter1, inter2)
                        inter = inter.tolist()
                        signal_index = inter
                        signal_index = np.array(signal_index)
                        signal_index = signal_index.astype(int)
                        signal_index = signal_index.tolist()

                    if UTB_signal_max > now:
                        temp1 = np.where(UTB_abdom < (now))
                        temp2 = np.where(UTB_abdom > (UTB_signal_min))
                        inter1 = np.intersect1d(temp1, temp2)
                        inter1 = inter1.tolist()
                        temp11 = np.where(UTB_abdom > ((now - TIT)))
                        temp22 = np.where(UTB_abdom < ((now - TIT) + SSW / 2))
                        inter2 = np.intersect1d(temp11, temp22)
                        inter2 = inter2.tolist()
                        inter = np.union1d(inter1, inter2)
                        inter = inter.tolist()
                        signal_index = inter
                        signal_index = np.array(signal_index)
                        signal_index = signal_index.astype(int)
                        signal_index = signal_index.tolist()

                    QF_abdom_index = np.where(QF_abdom)
                    all_data_index = QF_abdom_index[0].tolist()
                    noise_index = diff(all_data_index, signal_index)
                    SIGNAL = QF_abdom[signal_index]
                    UTB_SIGNAL = UTB_abdom[signal_index]
                    TOA_SIGNAL = TOAS_abdom[signal_index]
                    UNIX_TOA_SIGNAL = UTB_abdom[signal_index] + TOAS_abdom[signal_index]
                    if len(noise_index) != 0:
                        NOISE = QF_abdom[noise_index]
                        NOISElist = NOISE.tolist()
                        NOISElist.sort(reverse=True)
                        NOISE = NOISE.tolist()
                        NOISE.sort(reverse=True)
                        noise_threshold = max(
                            NOISE)  # To be sure not to take signal

                    # First filter: 22 greatest

                    Security_Number = len(SIGNAL)  # To be sure to take all the pulses

                    SIGNAL = SIGNAL.tolist()
                    SIGNAL_OLD = np.array(SIGNAL)
                    SIGNAL.sort(reverse=True)
                    QF_first = SIGNAL[0:Security_Number]

                    # Second filter: delete duplicates (Delete if Unixtimebase + ToA is the same)

                    QF_second = QF_first

                    R = []
                    for r in np.arange(len(QF_first)):
                        R.append(np.where(SIGNAL_OLD == QF_first[r])[0][0])
                    UTB_first = np.array(UTB_SIGNAL.tolist())[R]
                    TOA_first = np.array(TOA_SIGNAL.tolist())[R]

                    UNIX_TOA = UTB_first + TOA_first
                    UNIX_TOA = UNIX_TOA.tolist()

                    UNIX_TOA_index = []
                    for x in set(UNIX_TOA):
                        if UNIX_TOA.count(x) > 1:
                            UNIX_TOA_index.append(duplicates(UNIX_TOA, x))

                    ind_del = []
                    for i in range(len(UNIX_TOA_index)):
                        ind_del.append(UNIX_TOA_index[i][0])

                    for ide in sorted(ind_del, reverse=True):
                        del QF_second[ide]

                    QF_second.sort(reverse=True)

                    # Third filter: If there are more than 11 elements I will eliminate the worst

                    if len(QF_second) > 11:
                        QF_second = np.array(QF_second)
                        QF_third = [
                            k for k in QF_second
                            if (np.where(QF_second == k)[0][0] < 11)
                        ]
                    else:
                        QF_third = QF_second

                    # Fourth filter: I remove the data if it is below the maximum noise
                    if len(noise_index) != 0:
                        QF_fourth = [
                            k for k in QF_third
                            if k > (noise_threshold + (10 * np.std(NOISE)))
                        ]
                    else:
                        QF_fourth = QF_third

                    # Fifth filter: Check if the clicks are interspersed in the right way

                    QF_fifth = QF_fourth
                    Q = []
                    for q in np.arange(len(QF_fifth)):
                        Q.append(np.where(SIGNAL_OLD == QF_fifth[q])[0][0])
                    UTB_fourth = np.array(UTB_SIGNAL.tolist())[Q]
                    UTB_fourth_l = UTB_fourth.tolist()
                    D = []
                    for g in np.arange(len(UTB_fourth_l)):
                        if ((np.mod((UTB_fourth_l[g] - UTB_fourth_l[0]), 5) > 2
                             and np.mod(
                                 (UTB_fourth_l[g] - UTB_fourth_l[0]), 5) < 4)
                                or
                            (np.mod(
                                (UTB_fourth_l[g] - UTB_fourth_l[0]), 5) > 5)
                            ):
                            D.append(g)
                    for d in sorted(D, reverse=True):
                        del QF_fifth[d]

                    # Sixth filter:
                    if len(noise_index) != 0:
                        QF_sixth = [
                            k for k in QF_fifth
                            if (2*abs(k - max(QF_fifth)) < abs(k - noise_threshold))
                        ]
                    else:
                        QF_sixth = QF_fifth

                    QF_OK = QF_sixth

                    P = []
                    for p in np.arange(len(QF_OK)):
                        P.append(np.where(SIGNAL_OLD == QF_OK[p])[0][0])
                    UTB_OK = np.array(UTB_SIGNAL.tolist())[P]
                    UTB_OK_l = UTB_OK.tolist()

                    UTB_MIN.append(min(UTB_OK_l))

                    max_QF = max(QF_OK)

                    QF_MAX.append(max_QF)

                    NUM = len(QF_OK)  # Number of pulses
                    print(NUM)

                    if (NUM > 7):
                        N_Pulses_Indicator_DU.append(1.5)
                    elif (NUM < 8 and NUM > 3):
                        N_Pulses_Indicator_DU.append(0.5)
                    elif (NUM < 4 and NUM > 0):
                        N_Pulses_Indicator_DU.append(-0.5)
                    elif (NUM == 0):
                        N_Pulses_Indicator_DU.append(-1.5)

                except (
                        TypeError, ValueError, http.client.RemoteDisconnected, ssl.SSLError
                ):  # TypeError if no data found for a certain piezo, ValueError if there are zero data for a certain piezo
                    N_Pulses_Indicator_DU.append(-1.5)
                except (
                        http.client.RemoteDisconnected, ssl.SSLError
                ):  # Bad connection to the DB
                    N_Pulses_Indicator_DU.append(-2.5)                    

            # To avoid to take wrong beacon signals

            dim = np.size(QF_MAX)
            pulse_inter = 5.04872989654541

            for i in range(dim - 1):

                if (np.mod((UTB_MIN[i] - UTB_MIN[i + 1]), pulse_inter) < 10**-3
                        or np.mod(
                            (UTB_MIN[i] - UTB_MIN[i + 1]), pulse_inter) > 5):
                    if QF_MAX[i] <= QF_MAX[i + 1]:
                        N_Pulses_Indicator_DU[3 * dom + i] = -1.5
                    else:
                        N_Pulses_Indicator_DU[3 * dom + i + 1] = -1.5
                if i == 0 and dim == 3:
                    if (np.mod(
                        (UTB_MIN[i] -
                         UTB_MIN[i + 2]), pulse_inter) < 10**-3 or np.mod(
                             (UTB_MIN[i] - UTB_MIN[i + 2]), pulse_inter) > 5):
                        if QF_MAX[i] <= QF_MAX[i + 2]:
                            N_Pulses_Indicator_DU[3 * dom + i] = -1.5
                        else:
                            N_Pulses_Indicator_DU[3 * dom + i + 2] = -1.5
                        

        N_Pulses_Indicator.append(N_Pulses_Indicator_DU)

    fig, ax = plt.subplots(figsize=(9, 7))

    duab = []
    DUs = []
    for du in DUS_cycle:
        duabdu = []
        duab1 = (du - 0.2) * np.ones(N_DOMS + 1)
        duab2 = (du) * np.ones(N_DOMS + 1)
        duab3 = (du + 0.2) * np.ones(N_DOMS + 1)
        duabdu.append(duab1)
        duabdu.append(duab2)
        duabdu.append(duab3)
        duab.append(duabdu)
        DUs.append(np.array(N_Pulses_Indicator[du - 1]))

    iAB1 = []
    iAB2 = []
    iAB3 = []
    for i in DOMS:
        iAB1.append(3 * i)
        iAB2.append(3 * i + 1)
        iAB3.append(3 * i + 2)

    colorsList = [(0.6, 0, 1), (0, 0, 0), (1, 0.3, 0), (1, 1, 0), (0.2, 0.9, 0)]
    CustomCmap = matplotlib.colors.ListedColormap(colorsList)
    bounds = [-3, -2, -1, 0, 1, 2]
    norma = colors.BoundaryNorm(bounds, CustomCmap.N)
    for du in DUS:
        color = ax.scatter(duab[du - 1][0],
                           DOMS,
                           s=20,
                           c=DUs[du - 1][iAB1],
                           norm=norma,
                           marker='s',
                           cmap=CustomCmap)
        color = ax.scatter(duab[du - 1][1],
                           DOMS,
                           s=20,
                           c=DUs[du - 1][iAB2],
                           norm=norma,
                           marker='s',
                           cmap=CustomCmap)
        color = ax.scatter(duab[du - 1][2],
                           DOMS,
                           s=20,
                           c=DUs[du - 1][iAB3],
                           norm=norma,
                           marker='s',
                           cmap=CustomCmap)

    cbar = plt.colorbar(color)
    cbar.ax.get_yaxis().set_ticks([])
    for j, lab in enumerate(
        ['$No DB conn.$','$0. pings$', '$1-3 pings$', '$4-7 pings$', '$>7. pings$']):
        cbar.ax.text(4, (1.5 * j + 1) / 8.0, lab, ha='center', va='center')
    cbar.ax.get_yaxis().labelpad = 18

    ax.set_xticks(np.arange(1, max(DUS) + 1, step=1))
    ax.set_yticks(np.arange(0, 19, step=1))
    ax.grid(color='k', linestyle='-', linewidth=0.2)
    ax.set_xlabel('DUs', fontsize=18)
    ax.set_ylabel('Floors', fontsize=18)
    ts = now
    DATE = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    ax.set_title(
        r' %.16s Detection of the pings emitted by autonomous beacons' % DATE,
        fontsize=10)

    my_path = os.path.abspath(directory)
    my_file = 'Online_Acoustic_Monitoring.png'

    fig.savefig(os.path.join(my_path, my_file))
    plt.close('all')
    
    print(time.time())

    check = False
    check_time = time.time() - now - TIT
    print(check_time)

    time.sleep(abs(TIT - check_time))
    check = True
