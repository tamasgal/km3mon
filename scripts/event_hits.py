#!/usr/bin/env python
# coding=utf-8
# Filename: event_hits.py
# Author: Tamas Gal <tgal@km3net.de>
# vim: ts=4 sw=4 et
"""
Monitors hits and triggered hits on each DOM, based on events.

Usage:
    event_hits.py [options]
    event_hits.py (-h | --help)

Options:
    -l LIGIER_IP    The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT  The port of the ligier [default: 5553].
    -d DET_ID       Detector ID [default: 29].
    -o PLOT_DIR     The directory to save the plot [default: www/plots].
    -h --help       Show this screen.

"""
from __future__ import division

from datetime import datetime
from collections import deque, defaultdict
from functools import partial
import math
import os
import shutil
import time
import threading
from io import BytesIO

import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as md
from matplotlib.colors import LogNorm
from matplotlib import pylab
import seaborn as sns
import pandas as pd
import numpy as np

from km3pipe import Pipeline, Module, Geometry
from km3pipe.dataclasses import HitSeries
from km3pipe.common import Queue, Empty
from km3pipe.hardware import Detector
from km3pipe.io import CHPump
from km3pipe.io.daq import (DAQProcessor, DAQPreamble, DAQSummaryslice,
                               DAQEvent)
from km3pipe.time import tai_timestamp
import km3pipe.style
km3pipe.style.use('km3pipe')


PLOTS_PATH = 'km3web/plots'
N_DOMS = 18
N_DUS = 2
geometry = Geometry(det_id=29)
detector = geometry.detector

xfmt = md.DateFormatter('%Y-%m-%d %H:%M')


class DOMHits(Module):
    def configure(self):
        self.run = True
        self.max_events = 1000
        self.hits = deque(maxlen=1000)
        self.triggered_hits = deque(maxlen=1000)
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.plot).start()

    def process(self, blob):
        tag = str(blob['CHPrefix'].tag)

        if not tag == 'IO_EVT':
            return blob

        data = blob['CHData']
        data_io = BytesIO(data)
        preamble = DAQPreamble(file_obj=data_io)
        event = DAQEvent(file_obj=data_io)
        with self.lock:
            hits = np.zeros(N_DOMS * N_DUS)
            for dom_id, _, _, _ in event.snapshot_hits:
                du, floor, _ = detector.doms[dom_id]
                hits[(du - 1) * N_DOMS + floor - 1] += 1
            self.hits.append(hits)
            triggered_hits = np.zeros(N_DOMS * N_DUS)
            for dom_id, _, _, _, _ in event.triggered_hits:
                du, floor, _ = detector.doms[dom_id]
                triggered_hits[(du - 1) * N_DOMS + floor - 1] += 1
            self.triggered_hits.append(triggered_hits)

        return blob

    def plot(self):
        while self.run:
            with self.lock:
                self.create_plots()
            time.sleep(50)

    def create_plots(self):
        if len(self.hits) > 0:
            self.create_plot(self.hits, "Hits on DOMs", 'hits_on_doms')
        if len(self.triggered_hits) > 0:
            self.create_plot(self.triggered_hits, "Triggered Hits on DOMs",
                        'triggered_hits_on_doms')

    def create_plot(self, hits, title, filename):
        fig, ax = plt.subplots(figsize=(16,8))
        ax.grid(True)
        ax.set_axisbelow(True)
        hit_matrix = np.array([np.array(x) for x in hits]).transpose()
        im = ax.matshow(hit_matrix,
                  interpolation='nearest', filternorm=None, cmap='plasma',
                  aspect='auto', origin='lower', zorder=3,
                  norm=LogNorm(vmin=1, vmax=np.amax(hit_matrix)))
        yticks = np.arange(N_DOMS * N_DUS)
        ytick_labels = ["DU{0:0.0f}-DOM{1:02d}"
                        .format(np.ceil((y+1)/N_DOMS), y % (N_DOMS) + 1) \
                        for y in yticks]
        ax.set_yticks(yticks);
        ax.set_yticklabels(ytick_labels);
        ax.tick_params(labelbottom=False)
        ax.tick_params(labeltop=False)
        ax.set_xlabel("event (latest on the right)")
        ax.set_title("{0} - via the last {1} Events\n{2} UTC"
                     .format(title, self.max_events,
                             datetime.utcnow().strftime("%c")))
        cb = fig.colorbar(im, pad = 0.05)
        cb.set_label("number of hits")

        fig.tight_layout()

        f = os.path.join(PLOTS_PATH, filename + '.png')
        f_tmp = os.path.join(PLOTS_PATH, filename + '_tmp.png')
        plt.savefig(f_tmp, dpi=120, bbox_inches="tight")
        plt.close('all')
        shutil.move(f_tmp, f)

    def finish(self):
        self.run = False
        if self.thread is not None:
            self.thread.stop()




def main():
    from docopt import docopt
    args = docopt(__doc__, version=VERSION)

    det_id = int(args['-d'])
    plots_path = args['-o']
    ligier_ip = args['-l']
    ligier_port = int(args['-p'])

    pipe = kp.Pipeline()
    pipe.attach(kp.io.ch.CHPump, host=ligier_ip,
                port=ligier_port,
                tags='IO_EVT, IO_SUM',
                timeout=60*60*24*7,
                max_queue=2000)
    pipe.attach(kp.io.daq.DAQProcessor)
    pipe.attach(DOMHits, det_id=det_id, plots_path=plots_path)
    pipe.drain()


if __name__ == '__main__':
    main()
