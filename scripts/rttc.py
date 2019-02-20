#!/usr/bin/env python
# coding=utf-8
# vim: ts=4 sw=4 et
"""
Cable round trip time monitor.

Usage:
    rttc.py [options] -d DET_ID
    rttc.py (-h | --help)

Options:
    -d DET_ID       Detector ID.
    -l DM_IP        The IP of the DetectorManager [default: 127.0.0.1].
    -o PLOT_DIR     The directory to save the plot [default: plots].
    -h --help       Show this screen.

"""
from __future__ import division

import os
from datetime import datetime
import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as md
import matplotlib.ticker as ticker
from matplotlib.colors import LogNorm
import numpy as np

from collections import deque, defaultdict
from functools import partial

import km3pipe as kp
from km3pipe import Pipeline, Module
import km3pipe.style
km3pipe.style.use('km3pipe')

from km3pipe.logger import logging


def main():
    from docopt import docopt
    args = docopt(__doc__)

    data = defaultdict(partial(deque, maxlen=1000))

    dm_ip = args['-l']
    det_id = int(args['-d'])
    plots_path = args['-o']

    detector = kp.hardware.Detector(det_id=det_id)
    clbmap = kp.db.CLBMap(det_id)
    dmm = kp.io.daq.DMMonitor(dm_ip, base='clb/outparams')

    params = []
    for du in detector.dus:
        params += ['wr_mu/%d/0' % du
                   ] + ['wr_delta/%d/0/%i' % (du, i) for i in range(4)]

    xfmt = md.DateFormatter('%Y-%m-%d %H:%M')

    session = dmm.start_session('rttc_monitoring', params)

    for values in session:
        for du in detector.dus:
            i = detector.dus.index(du)
            idx_start = i * 5
            idx_stop = idx_start + 5
            data[du].append((datetime.utcnow(),
                             [v['value'] for v in values[idx_start:idx_stop]]))

        n_dus = detector.n_dus
        fig, axes = plt.subplots(n_dus, figsize=(16, 4 * n_dus))
        for ax, du in zip(axes, detector.dus):
            times = []
            rttc = []
            for d in data[du]:
                times.append(d[0])
                wr_mu, wr_delta0, wr_delta1, wr_delta2, wr_delta3 = d[1]
                rttc_value = wr_mu - (
                    wr_delta0 + wr_delta1 + wr_delta2 + wr_delta3)
                rttc.append(rttc_value)

            ax.plot(times, rttc, marker="X", markersize=6, linestyle='None')

            clb = clbmap.base(du)
            ax.set_title("RTTC for CLB %s in Det ID %d" % (clb.upi, det_id))
            ax.set_xlabel('time [UTC]')
            ax.set_ylabel('RTTC [ps]')
            ax.xaxis.set_major_formatter(xfmt)
        plt.savefig(
            os.path.join(plots_path, 'rttc.png'), dpi=120, bbox_inches="tight")
        plt.close('all')


if __name__ == '__main__':
    main()
