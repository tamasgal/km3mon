#!/usr/bin/env python
# coding=utf-8
# vim: ts=4 sw=4 et
"""
Creates z-t-plots for every DU.

Usage:
    ztplot.py [options]
    ztplot.py (-h | --help)

Options:
    -l LIGIER_IP    The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT  The port of the ligier [default: 5553].
    -d DET_ID       Detector ID [default: 29].
    -o PLOT_DIR     The directory to save the plot [default: plots].
    -h --help       Show this screen.

"""
from __future__ import division

from datetime import datetime
from collections import deque
import os
import queue
import shutil
import time
import threading

import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as md
import matplotlib.ticker as ticker
from matplotlib.colors import LogNorm
import numpy as np

import km3pipe as kp
from km3pipe import Pipeline, Module
from km3pipe.calib import Calibration
from km3pipe.hardware import Detector
from km3pipe.io import CHPump
from km3pipe.io.daq import (DAQProcessor, DAQPreamble, DAQSummaryslice,
                            DAQEvent)
import km3pipe.style
km3pipe.style.use('km3pipe')

from km3pipe.logger import logging

# for logger_name, logger in logging.Logger.manager.loggerDict.iteritems():
#     if logger_name.startswith('km3pipe.'):
#         print("Setting log level to debug for '{0}'".format(logger_name))
#         logger.setLevel("DEBUG")

# xfmt = md.DateFormatter('%Y-%m-%d %H:%M')
lock = threading.Lock()


class ZTPlot(Module):
    def configure(self):
        self.plots_path = self.require('plots_path')
        det_id = self.require('det_id')
        self.calib = kp.calib.Calibration(det_id=det_id)

        self.run = True
        self.max_queue = 3
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self.plot)
        self.thread.start()

    def process(self, blob):
        if 'Hits' not in blob:
            return blob

        hits = blob['Hits'].serialise(to='pandas')
        hits = self.calib.apply(hits)
        event_info = blob['EventInfo']

        if len(np.unique(hits[hits.triggered == True].du)) < 2:
            print("Skipping...")
            return blob

        print("OK")
        # print("Event queue size: {0}".format(self.queue.qsize()))
        if self.queue.qsize() < self.max_queue:
            self.queue.put((event_info, hits))

        return blob

    def plot(self):
        while self.run:
            try:
                event_info, hits = self.queue.get(timeout=50)
            except queue.Empty:
                continue
            with lock:
                self.create_plot(event_info, hits)

    def create_plot(self, event_info, hits):
        print(self.__class__.__name__ + ": updating plot.")
        dus = set(hits.du)

        n_plots = len(dus)
        n_cols = int(np.ceil(np.sqrt(n_plots)))
        n_rows = int(n_plots / n_cols) + (n_plots % n_cols > 0)
        fig, axes = plt.subplots(
            ncols=n_cols,
            nrows=n_rows,
            sharex=True,
            sharey=True,
            figsize=(16, 8))

        for ax, (du, du_hits) in zip(axes.flat, hits.groupby("du")):
            trig_hits = du_hits[du_hits.triggered == True]

            ax.scatter(du_hits.time, du_hits.pos_z, c='#09A9DE', label='hit')
            ax.scatter(
                trig_hits.time,
                trig_hits.pos_z,
                c='#FF6363',
                label='triggered hit')
            ax.set_title('DU{0}'.format(du), fontsize=16, fontweight='bold')

        for ax in axes.flat:
            ax.tick_params(labelsize=16)
            ax.yaxis.set_major_locator(ticker.MultipleLocator(200))
            xlabels = ax.get_xticklabels()
            for label in xlabels:
                label.set_rotation(45)

        plt.suptitle(
            "FrameIndex {0}, TriggerCounter {1}\n{2} UTC".format(
                event_info.frame_index, event_info.trigger_counter,
                datetime.utcfromtimestamp(event_info.utc_seconds)),
            fontsize=16)
        fig.text(0.5, 0.01, 'time [ns]', ha='center')
        fig.text(0.08, 0.5, 'z [m]', va='center', rotation='vertical')
        #        plt.tight_layout()

        filename = 'ztplot'
        f = os.path.join(self.plots_path, filename + '.png')
        f_tmp = os.path.join(self.plots_path, filename + '_tmp.png')
        plt.savefig(f_tmp, dpi=120, bbox_inches="tight")
        plt.close('all')
        shutil.move(f_tmp, f)

    def finish(self):
        self.run = False
        if self.thread is not None:
            self.thread.stop()


def main():
    from docopt import docopt
    args = docopt(__doc__)

    det_id = int(args['-d'])
    plots_path = args['-o']
    ligier_ip = args['-l']
    ligier_port = int(args['-p'])

    pipe = kp.Pipeline()
    pipe.attach(
        kp.io.ch.CHPump,
        host=ligier_ip,
        port=ligier_port,
        tags='IO_EVT, IO_SUM',
        timeout=60 * 60 * 24 * 7,
        max_queue=2000)
    pipe.attach(kp.io.daq.DAQProcessor)
    pipe.attach(ZTPlot, det_id=det_id, plots_path=plots_path)
    pipe.drain()


if __name__ == '__main__':
    main()
