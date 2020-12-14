#!/usr/bin/env python
# coding=utf-8
# vim: ts=4 sw=4 et
"""
Runs the AHRS calibration online.

Usage:
    ahrs_calibration.py [options]
    ahrs_calibration.py (-h | --help)

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
from functools import partial
import io
import os
import time
import threading

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as md
import seaborn as sns

from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

import km3pipe as kp
from km3pipe.io.daq import TMCHData
from km3modules.ahrs import fit_ahrs, get_latest_ahrs_calibration
import km3pipe.style
km3pipe.style.use('km3pipe')


class CalibrateAHRS(kp.Module):
    def configure(self):
        self.plots_path = self.require('plots_path')
        det_id = self.require('det_id')
        self.time_range = self.get('time_range', default=24 * 3)  # hours
        self.detector = kp.hardware.Detector(det_id=det_id)
        self.dus = set()

        self.clbmap = kp.db.CLBMap(det_oid=det_id)

        self.cuckoo = kp.time.Cuckoo(60, self.create_plot)
        self.cuckoo_log = kp.time.Cuckoo(10, print)

        self.data = {}
        self.queue_size = 100000

        self.lock = threading.Lock()
        self.index = 0

    def _register_du(self, du):
        """Create data cache for DU"""
        self.data[du] = {}
        for ahrs_param in ('yaw', 'pitch', 'roll'):
            self.data[du][ahrs_param] = defaultdict(
                partial(deque, maxlen=self.queue_size))
        self.data[du]['times'] = defaultdict(
            partial(deque, maxlen=self.queue_size))
        self.dus.add(du)

    def process(self, blob):
        self.index += 1
        if self.index % 29 != 0:
            return blob
        now = datetime.utcnow()
        tmch_data = TMCHData(io.BytesIO(blob['CHData']))
        dom_id = tmch_data.dom_id
        clb = self.clbmap.dom_ids[dom_id]
        if clb.floor == 0:
            self.log.info("Skipping base CLB")
            return blob

        yaw = tmch_data.yaw
        calib = get_latest_ahrs_calibration(clb.upi, max_version=4)

        if calib is None:
            self.log.warning("No calibration found for CLB UPI '%s'", clb.upi)
            return blob

        du = clb.du
        if du not in self.dus:
            self._register_du(du)
        cyaw, cpitch, croll = fit_ahrs(tmch_data.A, tmch_data.H, *calib)
        self.cuckoo_log("DU{}-DOM{} (random pick): calibrated yaw={}".format(
            clb.du, clb.floor, cyaw))
        with self.lock:
            self.data[du]['yaw'][clb.floor].append(cyaw)
            self.data[du]['pitch'][clb.floor].append(cpitch)
            self.data[du]['roll'][clb.floor].append(croll)
            self.data[du]['times'][clb.floor].append(now)

        self.cuckoo.msg()
        return blob

    def create_plot(self):
        print(self.__class__.__name__ + ": updating plot.")
        if self.time_range > 24:
            xfmt = md.DateFormatter('%Y-%m-%d %H:%M')
        else:
            xfmt = md.DateFormatter('%H:%M')
        xlim = (datetime.utcfromtimestamp(time.time() -
                                          self.time_range * 60 * 60),
                datetime.utcnow())
        for du in self.dus:
            data = self.data[du]
            for ahrs_param in data.keys():
                fig, ax = plt.subplots(figsize=(16, 6))
                sns.set_palette("husl", 18)
                ax.set_title("AHRS {} Calibration on DU{}\n{}".format(
                    ahrs_param, du, datetime.utcnow()))
                ax.set_xlabel("UTC time")
                ax.xaxis.set_major_formatter(xfmt)
                ax.set_ylabel(ahrs_param)
                with self.lock:
                    for floor in sorted(data[ahrs_param].keys()):
                        ax.plot(data['times'][floor],
                                data[ahrs_param][floor],
                                marker='.',
                                linestyle='none',
                                label="Floor {}".format(floor))
                ax.set_xlim(xlim)
                lgd = plt.legend(bbox_to_anchor=(1.005, 1),
                                 loc=2,
                                 borderaxespad=0.)
                fig.tight_layout()
                plt.savefig(os.path.join(
                    self.plots_path,
                    ahrs_param + '_calib_du{}.png'.format(du)),
                            bbox_extra_artists=(lgd, ),
                            bbox_inches='tight')
                plt.close('all')


def main():
    from docopt import docopt
    args = docopt(__doc__)

    det_id = int(args['-d'])
    plots_path = args['-o']
    ligier_ip = args['-l']
    ligier_port = int(args['-p'])

    pipe = kp.Pipeline()
    pipe.attach(kp.io.ch.CHPump,
                host=ligier_ip,
                port=ligier_port,
                tags='IO_MONIT',
                timeout=60 * 60 * 24 * 7,
                max_queue=2000)
    pipe.attach(CalibrateAHRS, det_id=det_id, plots_path=plots_path)
    pipe.drain()


if __name__ == '__main__':
    main()
