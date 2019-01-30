#!/usr/bin/env python
# coding=utf-8
# Filename: dom_activity.py
# Author: Tamas Gal <tgal@km3net.de>
# vim: ts=4 sw=4 et
"""
Monitors the DOM activity.

Usage:
    dom_activity.py [options]
    dom_activity.py (-h | --help)

Options:
    -l LIGIER_IP    The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT  The port of the ligier [default: 5553].
    -d DET_ID       Detector ID [default: 29].
    -o PLOT_DIR     The directory to save the plot [default: plots].
    -h --help       Show this screen.

"""
from __future__ import division

from collections import deque, defaultdict
from functools import partial
from io import BytesIO
import os
import time

import matplotlib
matplotlib.use("Agg")

import km3pipe as kp
import km3pipe.style
from km3modules.plot import plot_dom_parameters

VERSION = "1.0"

km3pipe.style.use('km3pipe')


class DOMActivityPlotter(kp.Module):
    "Creates a plot with dots for each DOM, coloured based in their activity"

    def configure(self):
        self.plots_path = self.require('plots_path')
        det_id = self.require('det_id')
        self.detector = kp.hardware.Detector(det_id=det_id)
        self.index = 0
        self.last_activity = defaultdict(partial(deque, maxlen=4000))
        self.cuckoo = kp.time.Cuckoo(60, self.create_plot)

        self.log.warning("Starting DOM Activity monitor")

    def process(self, blob):
        self.index += 1
        if self.index % 30:
            return blob

        if 'RawSummaryslice' in blob:
            summaryslice = blob['RawSummaryslice']
            timestamp = summaryslice.header.time_stamp

            for dom_id, _ in summaryslice.summary_frames.items():
                du, dom, _ = self.detector.doms[dom_id]
                self.last_activity[(du, dom)] = timestamp

            self.cuckoo.msg()

        return blob

    def create_plot(self):
        print(self.__class__.__name__ + ": updating plot.")
        filename = os.path.join(self.plots_path, 'dom_activity.png')
        # now = kp.time.tai_timestamp()
        now = time.time()
        delta_ts = {}
        inactive_doms = {}
        for key, timestamp in self.last_activity.items():
            delta_t = now - timestamp
            delta_ts[key] = delta_t
            if delta_t > 300:
                inactive_doms[key] = delta_t
        if inactive_doms:
            msg = "WARNING: the following DOM(s) has been inactive:\n"
            for key, delta_t in inactive_doms.items():
                msg += "   DU{}-DOM{} for {:.1f}s\n"  \
                  .format(key[0], key[1], delta_t)
            self.log.warning(msg)
        plot_dom_parameters(
            delta_ts,
            self.detector,
            filename,
            'last activity [s]',
            "DOM Activity for DetID-{} - via Summary Slices".format(
                self.detector.det_id),
            vmin=0.0,
            vmax=15 * 60)


def main():
    from docopt import docopt
    args = docopt(__doc__, version=VERSION)

    det_id = int(args['-d'])
    plots_path = args['-o']
    ligier_ip = args['-l']
    ligier_port = int(args['-p'])

    pipe = kp.Pipeline()
    pipe.attach(
        kp.io.ch.CHPump,
        host=ligier_ip,
        port=ligier_port,
        tags='IO_SUM',
        timeout=60 * 60 * 24 * 7,
        max_queue=2000)
    pipe.attach(kp.io.daq.DAQProcessor)
    pipe.attach(DOMActivityPlotter, det_id=det_id, plots_path=plots_path)
    pipe.drain()


if __name__ == '__main__':
    main()
