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
from datetime import datetime
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


class IO_OLINEDistributions(kp.Module):
    def configure(self):
        self.fontsize = 16

        self.plots_path = self.require('plots_path')
        self.max_events = self.get('max_events', default=5000)
        self.zeniths    = deque(maxlen=self.max_events)
        self.qualities  = deque(maxlen=self.max_events)
        self.interval   = 60
        threading.Thread(target=self.plot).start()

    def process(self, blob):
        track = blob['RecoTrack']

        if track.status==1:
            zenith = np.cos(
                kp.math.angle_between([0, 0, -1], [track.dx, track.dy, track.dz]))
            self.zeniths.append(zenith)

            self.qualities.append(track.Q)

        return blob

    def plot(self):
        while True:
            time.sleep(self.interval)
            self.create_zenith_plot()
            self.create_quality_plot()


    def create_quality_plot(self):
        n = len(self.qualities)
      
        plt.clf()
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.hist(
            self.qualities,
            bins=100,
            label="JGandalf (last %d events)" % n,
            histtype="step",
            normed=True,
            lw=3)
        ax.set_title(
            "Quality distribution of online track reconstructions\n%s UTC" %
            datetime.utcnow().strftime("%c"))
        ax.set_xlabel(r"Quality", fontsize=self.fontsize)
        ax.set_ylabel("normed count", fontsize=self.fontsize)
        ax.tick_params(labelsize=self.fontsize)
        ax.set_yscale("log")
        plt.legend(fontsize=self.fontsize, loc=2)
        filename = os.path.join(self.plots_path, 'gandalf_quality.png')
        plt.savefig(filename, dpi=120, bbox_inches="tight")
        plt.close('all')

    def create_zenith_plot(self):
        n = len(self.zeniths)

        plt.clf()
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.hist(
            self.zeniths,
            bins=180,
            label="JGandalf (last %d events)" % n,
            histtype="step",
            normed=True,
            lw=3)
        ax.set_title(
            "Zenith distribution of online track reconstructions\n%s UTC" %
            datetime.utcnow().strftime("%c"))
        ax.set_xlabel(r"cos(zenith)", fontsize=self.fontsize)
        ax.set_ylabel("normed count", fontsize=self.fontsize)
        ax.tick_params(labelsize=self.fontsize)
        ax.set_yscale("log")
        plt.legend(fontsize=self.fontsize, loc=2)
        filename = os.path.join(self.plots_path, 'gandalf_zenith.png')
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
    pipe.attach(IO_OLINEDistributions, plots_path=plots_path)
    pipe.drain()


if __name__ == '__main__':
    main()
