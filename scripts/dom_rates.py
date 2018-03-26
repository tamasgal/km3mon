#!/usr/bin/env python
# coding=utf-8
# Filename: dom_rates.py
# Author: Tamas Gal <tgal@km3net.de>
# vim: ts=4 sw=4 et
"""
Monitors DOM rates.

Usage:
    dom_rates.py [options]
    dom_rates.py (-h | --help)

Options:
    -l LIGIER_IP    The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT  The port of the ligier [default: 5553].
    -d DET_ID       Detector ID [default: 29].
    -o PLOT_DIR     The directory to save the plot [default: plots].
    -h --help       Show this screen.

"""
from __future__ import division

from io import BytesIO
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")

import km3pipe as kp
import km3pipe.style
from km3modules.plot import plot_dom_parameters


VERSION = "1.0"
km3pipe.style.use('km3pipe')


class MonitorRates(kp.Module):
    """Creates a coloured dot for each DOM, representing their rates."""
    def configure(self):
        self.plots_path = self.require('plots_path')
        det_id = self.require('det_id')

        self.detector = kp.hardware.Detector(det_id=det_id)
        self.index = 0
        self.k40_2fold = {}
        self.rates = {}
        self.cuckoo = kp.time.Cuckoo(60, self.create_plot)
        self.n_slices = 0

        self.log.warning("Starting DOM rates monitor")

    def process(self, blob):
        """Store the rates from summary slices"""
        self.index += 1
        if self.index % 30:
            return blob

        data = blob['CHData']
        data_io = BytesIO(data)
        preamble = kp.io.daq.DAQPreamble(file_obj=data_io)  # noqa
        summaryslice = kp.io.daq.DAQSummaryslice(file_obj=data_io)
        self.rates = {}  # TODO: review this hack
        for dom_id, rates in summaryslice.summary_frames.items():
            du, dom, _ = self.detector.doms[dom_id]
            self.rates[(du, dom)] = np.sum(rates) / 1000

        self.cuckoo.msg()

        return blob

    def create_plot(self):
        """Creates the actual plot"""
        print(self.__class__.__name__ + ": updating plot.")

        filename = os.path.join(self.plots_path, 'dom_rates.png')
        plot_dom_parameters(self.rates, self.detector, filename,
                            'rate [kHz]',
                            "DOM Rates",
                            vmin=200, vmax=400,
                            cmap='coolwarm', missing='black',
                            under='darkorchid', over='deeppink')
        print("done")


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
                tags='IO_SUM',
                timeout=60*60*24*7,
                max_queue=2000)
    pipe.attach(kp.io.daq.DAQProcessor)
    pipe.attach(MonitorRates, det_id=det_id, plots_path=plots_path)
    pipe.drain()


if __name__ == '__main__':
    main()
