#!/usr/bin/env python
# coding=utf-8
# Filename: pmt_hrv.py
# Author: Tamas Gal <tgal@km3net.de>
# vim: ts=4 sw=4 et
"""
Monitors HRV flags of PMTs.

Usage:
    pmt_hrv.py [options]
    pmt_hrv.py (-h | --help)

Options:
    -l LIGIER_IP    The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT  The port of the ligier [default: 5553].
    -u DU           The DU to monitor [default: 1].
    -d DET_ID       Detector ID [default: 29].
    -i INTERVAL     Time interval for one pixel [default: 10].
    -o PLOT_DIR     The directory to save the plot [default: plots].
    -h --help       Show this screen.

"""
from datetime import datetime
import io
import os
from collections import defaultdict
import threading
import time

import numpy as np
import matplotlib
matplotlib.use('Agg')

import km3pipe as kp
from km3pipe.io.daq import TMCHData
import matplotlib.pyplot as plt
import km3pipe.style as kpst
kpst.use("km3pipe")

__author__ = "Tamas Gal"
__email__ = "tgal@km3net.de"

VERSION = "1.0"
log = kp.logger.logging.getLogger("PMTrates")


class PMTHRV(kp.Module):
    def configure(self):
        self.detector = self.require("detector")
        self.du = self.require("du")
        self.interval = self.get("interval", default=10)
        self.plot_path = self.get("plot_path", default="plots")
        self.filename = self.get("filename", default="pmt_hrv.png")
        self.max_x = 800
        self.index = 0
        self.hrv = defaultdict(list)
        self.hrv_matrix = np.full((18*31, self.max_x), np.nan)
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, args=())
        self.thread.daemon = True
        self.thread.start()

    def run(self):
        interval = self.interval
        while True:
            time.sleep(interval)
            now = datetime.now()
            self.add_column()
            self.update_plot()
            with self.lock:
                self.rates = defaultdict(list)
            delta_t = (datetime.now() - now).total_seconds()
            remaining_t = self.interval - delta_t
            log.info("Delta t: {} -> waiting for {}s"
                     .format(delta_t, self.interval - delta_t))
            if(remaining_t < 0):
                log.error("Can't keep up with plot production. "
                          "Increase the interval!")
                interval = 1
            else:
                interval = remaining_t

    def add_column(self):
        m = np.roll(self.hrv_matrix, -1, 1)
        y_range = 18*31
        mean_hrv = np.full(y_range, np.nan)
        for i in range(y_range):
            if i not in self.hrv:
                continue
            mean_hrv[i] = np.mean(self.hrv[i])

        m[:, self.max_x - 1] = mean_hrv
        self.hrv_matrix = m

    def update_plot(self):
        filename = os.path.join(self.plot_path, self.filename)
        print("Updating plot at {}".format(filename))
        now = time.time()
        max_x = self.max_x
        interval = self.interval

        def xlabel_func(timestamp):
            return datetime.utcfromtimestamp(timestamp).strftime("%H:%M")

        m = self.hrv_matrix
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.imshow(m, origin='lower', interpolation='none')
        ax.set_title("HRV Ratios (Monitoring Channel) for DetID-{} DU-{}\n"
                     "PMTs ordered from top to bottom - {}"
                     .format(self.detector.det_id, self.du, datetime.utcnow()))
        ax.set_xlabel("UTC time [{}s/px]".format(interval))
        plt.yticks([i*31 for i in range(18)],
                   ["Floor {}".format(f) for f in range(1, 19)])
        xtics_int = range(0, max_x, int(max_x/10))
        plt.xticks([i for i in xtics_int],
                   [xlabel_func(now-(max_x-i) * interval) for i in xtics_int])
        fig.tight_layout()
        plt.savefig(filename)
        plt.close('all')

    def process(self, blob):
        try:
            tmch_data = TMCHData(io.BytesIO(blob['CHData']))
        except ValueError:
            self.log.error("Could not parse binary data. Ignoring...")
            return blob

        dom_id = tmch_data.dom_id

        if dom_id not in self.detector.doms:
            return blob

        du, floor, _ = self.detector.doms[dom_id]

        if du != self.du:
            return blob

        hrv_flags = reversed("{0:b}".format(tmch_data.hrvbmp).zfill(32))

        y_base = (floor - 1) * 31

        for channel_id, hrv_flag in enumerate(hrv_flags):
            if channel_id > 30:
                break
            idx = y_base + kp.hardware.ORDERED_PMT_IDS[channel_id]
            with self.lock:
                self.hrv[idx].append(int(hrv_flag))

        return blob


def main():
    from docopt import docopt
    args = docopt(__doc__, version=VERSION)

    det_id = int(args['-d'])
    plot_path = args['-o']
    ligier_ip = args['-l']
    ligier_port = int(args['-p'])
    du = int(args['-u'])
    interval = int(args['-i'])

    detector = kp.hardware.Detector(det_id=det_id)

    pipe = kp.Pipeline(timeit=True)
    pipe.attach(kp.io.ch.CHPump,
                host=ligier_ip,
                port=ligier_port,
                tags='IO_MONIT',
                timeout=60*60*24*7,
                max_queue=2000)
    pipe.attach(PMTHRV,
                detector=detector,
                du=du,
                interval=interval,
                plot_path=plot_path)
    pipe.drain()


if __name__ == '__main__':
    main()
