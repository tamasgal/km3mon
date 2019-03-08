#!/usr/bin/env python
# coding=utf-8
# Filename: online_reco.py
# Author: Tamas Gal <tgal@km3net.de>
# vim: ts=4 sw=4 et
"""
Visualisation routines for online reconstruction.

Usage:
    online_reco.py [options]
    online_reco.py (-h | --help)

Options:
    -l LIGIER_IP    The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT  The port of the ligier [default: 5553].
    -o PLOT_DIR     The directory to save the plot [default: www/plots].
    -h --help       Show this screen.

"""
from collections import deque
import time
import os
import threading
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import km3pipe as kp
import km3pipe.style

km3pipe.style.use('km3pipe')


class ZenithDistribution(kp.Module):
    def configure(self):
        self.plots_path = self.require('plots_path')
        self.max_events = self.get('max_events', default=5000)
        self.zeniths = deque(maxlen=self.max_events)
        self.interval = 60
        threading.Thread(target=self.plot).start()

    def process(self, blob):
        track = blob['RecoTrack']
        zenith = np.cos(
            kp.math.angle_between([0, 0, -1], [track.dx, track.dy, track.dz]))
        self.zeniths.append(zenith)
        return blob

    def plot(self):
        while True:
            time.sleep(self.interval)
            self.create_plot()

    def create_plot(self):
        n = len(self.zeniths)
        n_ok = n - np.count_nonzero(np.isnan(self.zeniths))
        fontsize = 16

        roy_zeniths = -np.loadtxt("reco.txt")[-self.max_events:]
        roy_zeniths[np.abs(roy_zeniths) > .99] = np.nan
        n_roy = len(roy_zeniths)

        fig, ax = plt.subplots(figsize=(16, 8))
        ax.hist(
            self.zeniths,
            bins=180,
            label="JGandalf (last %d events)" % n,
            histtype="step",
            lw=3)
        ax.hist(
            roy_zeniths,
            bins=180,
            label="ROy (last %d events)" % n_roy,
            histtype="step",
            lw=3)
        ax.set_title("Zenith distribution of online track reconstructions")
        ax.set_xlabel(r"cos(zenith)", fontsize=fontsize)
        ax.set_ylabel("count", fontsize=fontsize)
        ax.tick_params(labelsize=fontsize)
        ax.set_yscale("log")
        filename = os.path.join(self.plots_path, 'track_reco.png')
        plt.savefig(filename, dpi=120, bbox_inches="tight")
        plt.close('all')


def main():
    from docopt import docopt
    args = docopt(__doc__)

    plots_path = args['-o']
    ligier_ip = args['-l']
    ligier_port = int(args['-p'])

    pipe = kp.Pipeline()
    pipe.attach(
        kp.io.ch.CHPump,
        host=ligier_ip,
        port=ligier_port,
        tags='IO_OLINE',
        timeout=60 * 60 * 24 * 7,
        max_queue=2000)
    pipe.attach(kp.io.daq.DAQProcessor)
    pipe.attach(ZenithDistribution, plots_path=plots_path)
    pipe.drain()


if __name__ == '__main__':
    main()
