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
    -o PLOT_DIR     The directory to save the plot [default: /plots].
    -h --help       Show this screen.

"""
from __future__ import division

import os
from datetime import datetime
import time
import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as md
import matplotlib.ticker as ticker
from matplotlib.colors import LogNorm
import numpy as np

from collections import deque, defaultdict, OrderedDict
from functools import partial

import km3db
import km3pipe as kp
from km3pipe import Pipeline, Module
import km3pipe.style
km3pipe.style.use('km3pipe')

from km3pipe.logger import logging


@kp.tools.timed_cache(hours=1)
def get_baseline_rttc(det_id, hours=24):
    """Retrieve the median and std RTTC values for a given time interval [h]"""
    print("Retrieving baseline RTTC")
    now = time.time()
    det_oid = km3db.tools.todetoid(det_id)
    sds = km3db.StreamDS(container="pd")
    det = kp.hardware.Detector(det_id=det_id)
    clbmap = km3db.CLBMap(det_oid=det_oid)
    runs = sds.runs(detid=det_id)
    latest_run = int(runs.tail(1).RUN)
    run_24h_ago = int(
        runs[runs.UNIXSTARTTIME < (now - 60 * 60 * hours) * 1000].tail(1).RUN)

    data = OrderedDict()
    for param in ['wr_mu'] + ['wr_delta[%d]' % i for i in range(4)]:
        data[param] = sds.datalognumbers(
            parameter_name=param,
            detid=det_oid,
            minrun=run_24h_ago,
            maxrun=latest_run)
    baselines = {}
    for du in det.dus:
        source_name = clbmap.base(du).upi
        du_data = OrderedDict()
        for param, df in data.items():
            values = df[df.SOURCE_NAME == source_name].DATA_VALUE.values
            if len(values) == 0:
                du_data[param] = (np.nan, np.nan)
                continue
            du_data[param] = (np.median(values), np.std(values))
        rttc_median = du_data['wr_mu'][0] - np.sum(
            [du_data[p][0] for p in list(du_data.keys())[1:]])
        rttc_std = du_data['wr_mu'][1] - np.sum(
            [du_data[p][1] for p in list(du_data.keys())[1:]])
        baselines[du] = (rttc_median, rttc_std)
    return baselines


def main():
    from docopt import docopt
    args = docopt(__doc__)

    data = defaultdict(partial(deque, maxlen=1000))

    dm_ip = args['-l']
    det_id = int(args['-d'])
    plots_path = args['-o']

    detector = kp.hardware.Detector(det_id=det_id)
    clbmap = km3db.CLBMap(det_id)
    dmm = kp.io.daq.DMMonitor(dm_ip, base='clb/outparams')

    params = []
    for du in detector.dus:
        params += ['wr_mu/%d/0' % du
                   ] + ['wr_delta/%d/0/%i' % (du, i) for i in range(4)]

    xfmt = md.DateFormatter('%Y-%m-%d %H:%M')

    session = dmm.start_session('rttc_monitoring', params)

    for values in session:
        baselines = get_baseline_rttc(det_id, hours=24)
        for du in detector.dus:
            i = detector.dus.index(du)
            idx_start = i * 5
            idx_stop = idx_start + 5
            data[du].append((datetime.utcnow(),
                             [v['value'] for v in values[idx_start:idx_stop]]))

        n_dus = detector.n_dus
        fig, axes = plt.subplots(n_dus, figsize=(16, 4 * n_dus))
        axes = [axes] if n_dus == 1 else axes.flatten()
        for ax, du in zip(axes, detector.dus):
            times = []
            rttc = []
            for d in data[du]:
                times.append(d[0])
                wr_mu, wr_delta0, wr_delta1, wr_delta2, wr_delta3 = d[1]
                rttc_value = wr_mu - (
                    wr_delta0 + wr_delta1 + wr_delta2 + wr_delta3)
                rttc.append(rttc_value)

            ax.plot(
                times,
                rttc,
                marker="X",
                markersize=6,
                linestyle='None',
                zorder=100)

            rttc_median = baselines[du][0]
            rttc_std = baselines[du][1]
            ax.axhline(y=rttc_median + rttc_std, color='r', lw=1, ls='--')
            ax.axhline(y=rttc_median - rttc_std, color='r', lw=1, ls='--')
            ax.axhline(y=rttc_median, color='r', lw=2, ls='-')

            clb = clbmap.base(du)
            ax.set_title("RTTC for base CLB %s of DU-%d in Det ID %d" %
                         (clb.upi, du, det_id))
            ax.set_xlabel('time [UTC]')
            ax.set_ylabel('RTTC [ps]')
            ax.xaxis.set_major_formatter(xfmt)
            ax.yaxis.set_major_formatter(ticker.ScalarFormatter())
            ax.yaxis.get_major_formatter().set_scientific(False)
            ax.yaxis.get_major_formatter().set_useOffset(False)
        plt.savefig(
            os.path.join(plots_path, 'rttc.png'), dpi=120, bbox_inches="tight")
        plt.close('all')


if __name__ == '__main__':
    main()
