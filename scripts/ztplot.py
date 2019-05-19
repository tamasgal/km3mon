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
import os
import queue
import shutil
import threading

import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

import km3pipe as kp
from km3pipe.io.daq import is_3dmuon, is_3dshower, is_mxshower
from km3modules.hits import count_multiplicities
import km3pipe.style
km3pipe.style.use('km3pipe')

from km3pipe.logger import logging

lock = threading.Lock()


class ZTPlot(kp.Module):
    def configure(self):
        self.plots_path = self.require('plots_path')
        self.ytick_distance = self.get('ytick_distance', default=200)
        self.min_dus = self.get('min_dus', default=1)
        self.det_id = self.require('det_id')
        self.t0set = None
        self.calib = None
        self.max_z = None

        self.sds = kp.db.StreamDS()

        self.index = 0

        self._update_calibration()

        self.run = True
        self.max_queue = 3
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self.plot, daemon=True)
        self.thread.start()

    def _update_calibration(self):
        self.print("Updating calibration")
        self.t0set = self.sds.t0sets(detid=self.det_id).iloc[-1]['CALIBSETID']
        self.calib = kp.calib.Calibration(det_id=self.det_id, t0set=self.t0set)
        self.max_z = round(np.max(self.calib.detector.pmts.pos_z) + 10, -1)

    def process(self, blob):
        if 'Hits' not in blob:
            return blob

        self.index += 1
        if self.index % 1000 == 0:
            self._update_calibration()

        hits = blob['Hits']
        hits = self.calib.apply(hits)
        event_info = blob['EventInfo']

        triggered_dus = np.unique(hits[hits.triggered == True].du)
        if len(triggered_dus) < self.min_dus:
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
        doms = set(hits.dom_id)
        fontsize = 16

        hits = hits.append_columns('multiplicity',
                                   np.ones(len(hits))).sorted(by='time')

        for dom in doms:
            dom_hits = hits[hits.dom_id == dom]
            mltps, m_ids = count_multiplicities(dom_hits.time)
            hits['multiplicity'][hits.dom_id == dom] = mltps

        time_offset = np.min(hits[hits.triggered == True].time)
        hits.time -= time_offset

        n_plots = len(dus)
        n_cols = int(np.ceil(np.sqrt(n_plots)))
        n_rows = int(n_plots / n_cols) + (n_plots % n_cols > 0)
        marker_fig, marker_axes = plt.subplots()  # for the marker size hack...
        fig, axes = plt.subplots(
            ncols=n_cols,
            nrows=n_rows,
            sharex=True,
            sharey=True,
            figsize=(16, 8),
            constrained_layout=True)

        axes = [axes] if n_plots == 1 else axes.flatten()

        dom_zs = self.calib.detector.pmts.pos_z[
            (self.calib.detector.pmts.du == min(dus))
            & (self.calib.detector.pmts.channel_id == 0)]

        for ax, du in zip(axes, dus):
            for z in dom_zs:
                ax.axhline(z, lw=1, color='b', ls='--', alpha=0.15)
            du_hits = hits[hits.du == du]
            trig_hits = du_hits[du_hits.triggered == True]

            ax.scatter(
                du_hits.time,
                du_hits.pos_z,
                s=du_hits.multiplicity * 30,
                c='#09A9DE',
                label='hit',
                alpha=0.5)
            ax.scatter(
                trig_hits.time,
                trig_hits.pos_z,
                s=trig_hits.multiplicity * 30,
                alpha=0.8,
                marker="+",
                c='#FF6363',
                label='triggered hit')
            ax.set_title(
                'DU{0}'.format(int(du)), fontsize=fontsize, fontweight='bold')

        for idx, ax in enumerate(axes):
            ax.set_ylim(0, self.max_z)
            ax.tick_params(labelsize=fontsize)
            ax.yaxis.set_major_locator(
                ticker.MultipleLocator(self.ytick_distance))
            xlabels = ax.get_xticklabels()
            for label in xlabels:
                label.set_rotation(45)

            if idx % n_cols == 0:
                ax.set_ylabel('z [m]', fontsize=fontsize)
            if idx >= len(axes) - n_cols:
                ax.set_xlabel('time [ns]', fontsize=fontsize)

        # The only way I could create a legend with matching marker sizes
        max_multiplicity = int(np.max(du_hits.multiplicity))
        custom_markers = [
            marker_axes.scatter(
                [], [], s=mult * 30, color='#09A9DE', lw=0, alpha=0.5)
            for mult in range(0, max_multiplicity)
        ] + [marker_axes.scatter([], [], s=30, marker="+", c='#FF6363')]
        axes[0].legend(
            custom_markers, ['multiplicity'] +
            ["       %d" % m
             for m in range(1, max_multiplicity)] + ['triggered'],
            scatterpoints=1,
            markerscale=1,
            loc='upper left',
            bbox_to_anchor=(1.005, 1))

        trigger_params = ' '.join([
            trig
            for trig, trig_check in (("MX", is_mxshower), ("3DM", is_3dmuon),
                                     ("3DS", is_3dshower))
            if trig_check(int(event_info.trigger_mask[0]))
        ])

        plt.suptitle(
            "z-t-Plot for DetID-{0} (t0set: {1}), Run {2}, FrameIndex {3}, "
            "TriggerCounter {4}, Overlays {5}, Trigger: {8}"
            "\n{7} UTC (time offset: {6} ns)".format(
                event_info.det_id[0], self.t0set, event_info.run_id[0],
                event_info.frame_index[0], event_info.trigger_counter[0],
                event_info.overlays[0], time_offset,
                datetime.utcfromtimestamp(
                    event_info.utc_seconds), trigger_params),
            fontsize=fontsize,
            y=1.05)

        filename = 'ztplot'
        f = os.path.join(self.plots_path, filename + '.png')
        f_tmp = os.path.join(self.plots_path, filename + '_tmp.png')
        plt.savefig(f_tmp, dpi=120, bbox_inches="tight")
        if len(doms) > 4:
            plt.savefig(os.path.join(self.plots_path, filename + '_5doms.png'))
        plt.close('all')
        shutil.move(f_tmp, f)

    def finish(self):
        self.run = False


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
