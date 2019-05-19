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
        self.plots = {
            'reco_zenith': {
                'title': 'Zenith distribution of online track reconstructions',
                'xlabel': 'cos(zenith)',
                'ylabel': 'normed count',
                'function': 'hist',
                'options': {
                    'bins': 180,
                    'histtype': "step",
                    'normed': True,
                    'lw': 3
                },
                'subplots': {
                    'gandalf': {
                        'data': deque(maxlen=self.max_events),
                        'subplot_options': {
                            'label': "JGandalf",
                        }
                    }
                }
            },
            'reco_quality': {
                'title': 'Quality of online track reconstructions',
                'xlabel': 'Quality',
                'ylabel': 'normed count',
                'function': 'hist',
                'options': {
                    'bins': 100,
                    'histtype': "step",
                    'normed': True,
                    'lw': 3
                },
                'subplots': {
                    'gandalf': {
                        'data': deque(maxlen=self.max_events),
                        'subplot_options': {
                            'label': "JGandalf",
                        }
                    }
                }
            },
        }
        self.plot_interval = 60  # [s]
        threading.Thread(target=self.plot).start()

    def process(self, blob):
        track = blob['RecoTrack']

        if track.status == 1:
            zenith = np.cos(
                kp.math.angle_between([0, 0, -1],
                                      [track.dx, track.dy, track.dz]))
            reco_name = track.reco

            self._add_reco_parameter('reco_zenith', reco_name, zenith)
            self._add_reco_parameter('reco_quality', reco_name, track.Q)

        return blob

    def _add_reco_parameter(self, parameter, reco_name, value):
        """Add the value to the parameter cache"""
        for reco, subplot in self.plots[parameter]['subplots']:
            if reco == reco_name:
                subplot['data'].append(value)

    def plot(self):
        while True:
            time.sleep(self.plot_interval)
            self.create_plots()

    def create_plots(self):
        for name, plot in self.plots.items():
            plt.clf()
            fig, ax = plt.subplots(figsize=(16, 8))
            for subplot in self.plots['subplots'].values():
                getattr(ax, plot['function'])(subplot['data'],
                                              **self.plots['options'],
                                              **subplot['options'])
            ax.set_title(plot['title'] +
                         "\n%s UTC" % datetime.utcnow().strftime("%c"))
            ax.set_xlabel(plot['xlabel'], fontsize=self.fontsize)
            ax.set_ylabel(plot['ylabel'], fontsize=self.fontsize)
            ax.tick_params(labelsize=self.fontsize)
            ax.set_yscale("log")
            plt.legend(fontsize=self.fontsize, loc=2)
            filename = os.path.join(self.plots_path, '%s.png' % name)
            plt.savefig(filename, dpi=120, bbox_inches="tight")
            plt.close('all')


def main():
    from docopt import docopt
    args = docopt(__doc__)

    plots_path = args['-o']
    ligier_ip = args['-l']
    ligier_port = int(args['-p'])

    pipe = kp.Pipeline()
    pipe.attach(kp.io.ch.CHPump,
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
