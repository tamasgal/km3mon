#!/usr/bin/env python
# coding=utf-8
# vim: ts=4 sw=4 et
"""
Generates trigger map plots.

Usage:
    live_triggermap.py [options]
    live_triggermap.py (-h | --help)

Options:
    -l LIGIER_IP    The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT  The port of the ligier [default: 5553].
    -d DET_ID       Detector ID [default: 29].
    -o PLOT_DIR     The directory to save the plot [default: plots].
    -h --help       Show this screen.

"""
from __future__ import division

from datetime import datetime
from collections import deque, defaultdict
import os
import shutil
import time
import threading

import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as md
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


class DOMHits(Module):
    def configure(self):
        self.plots_path = self.require('plots_path')
        det_id = self.require('det_id')
        self.det = kp.hardware.Detector(det_id=det_id)

        self.run = True
        self.max_events = 1000
        self.hits = deque(maxlen=1000)
        self.triggered_hits = deque(maxlen=1000)
        self.runchanges = defaultdict(int)
        self.current_run_id = 0
        self.n_events = 0

        self.thread = threading.Thread(target=self.plot).start()

    def process(self, blob):
        tag = str(blob['CHPrefix'].tag)

        if not tag == 'IO_EVT':
            return blob

        event_hits = blob['Hits']
        with lock:
            run_id = blob['EventInfo'].run_id[0]
            if run_id > self.current_run_id:
                self.current_run_id = run_id
            for _run_id in set(list(self.runchanges.keys()) + [run_id]):
                self.runchanges[_run_id] += 1
                if _run_id != self.current_run_id and \
                        self.runchanges[_run_id] > self.max_events:
                    self.print("Removing run {} from the annotation list".
                               format(_run_id))
                    del self.runchanges[_run_id]

            self.n_events += 1

            hits = np.zeros(self.det.n_doms)
            for dom_id in event_hits.dom_id:
                du, floor, _ = self.det.doms[dom_id]
                hits[(du - 1) * self.det.n_doms + floor - 1] += 1
            self.hits.append(hits)
            triggered_hits = np.zeros(self.det.n_doms)
            for dom_id in event_hits.dom_id[event_hits.triggered.astype(
                    'bool')]:
                du, floor, _ = self.det.doms[dom_id]
                triggered_hits[(du - 1) * self.det.n_doms + floor - 1] += 1
            self.triggered_hits.append(triggered_hits)

        return blob

    def plot(self):
        while self.run:
            with lock:
                self.create_plots()
            time.sleep(50)

    def create_plots(self):
        if len(self.hits) > 0:
            self.create_plot(self.hits, "Hits on DOMs", 'hitmap')
        if len(self.triggered_hits) > 0:
            self.create_plot(self.triggered_hits, "Trigger Map", 'triggermap')

    def create_plot(self, hits, title, filename):
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.grid(True)
        ax.set_axisbelow(True)
        hit_matrix = np.array([np.array(x) for x in hits]).transpose()
        im = ax.matshow(
            hit_matrix,
            interpolation='nearest',
            filternorm=None,
            cmap='plasma',
            aspect='auto',
            origin='lower',
            zorder=3,
            norm=LogNorm(vmin=1, vmax=np.amax(hit_matrix)))
        yticks = np.arange(self.det.n_doms)
        ytick_labels = [
            "DU{}-DOM{}".format(dom[0], dom[1])
            for dom in self.det.doms.values()
        ]
        ax.set_yticks(yticks)
        ax.set_yticklabels(ytick_labels)
        ax.tick_params(labelbottom=False)
        ax.tick_params(labeltop=False)
        ax.set_xlabel("event (latest on the right)")
        ax.set_title(
            "{0} for DetID-{1} - via the last {2} Events\n{3} UTC".format(
                title, self.det.det_id, self.max_events,
                datetime.utcnow().strftime("%c")))
        cb = fig.colorbar(im, pad=0.05)
        cb.set_label("number of hits")

        for run, n_events_since_runchange in self.runchanges.items():
            if n_events_since_runchange >= self.max_events:
                continue
            self.print("Annotating run {} ({} events passed)".format(
                run, n_events_since_runchange))
            x_pos = min(self.n_events,
                        self.max_events) - n_events_since_runchange
            plt.text(
                x_pos,
                self.det.n_doms,
                "\nRUN %s  " % run,
                rotation=60,
                verticalalignment='top',
                fontsize=12,
                color='black',
                zorder=10)
            ax.axvline(
                x_pos,
                linewidth=3,
                color='#ff0f5b',
                linestyle='--',
                alpha=0.8,
                zorder=10)

        fig.tight_layout()

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
        tags='IO_EVT',
        timeout=60 * 60 * 24 * 7,
        max_queue=2000)
    pipe.attach(kp.io.daq.DAQProcessor)
    pipe.attach(DOMHits, det_id=det_id, plots_path=plots_path)
    pipe.drain()


if __name__ == '__main__':
    main()
