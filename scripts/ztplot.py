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

import km3pipe.style
from km3modules.plot import ztplot
from km3modules.common import LocalDBService
from km3modules.communication import ELOGService
from km3pipe.io.daq import is_3dmuon, is_3dshower, is_mxshower
import km3pipe as kp
import numpy as np
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
from datetime import datetime
import os
import queue
import shutil
import threading
from urllib.error import URLError

import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')

km3pipe.style.use('km3pipe')

lock = threading.Lock()


class ZTPlot(kp.Module):
    def configure(self):
        self.plots_path = self.require('plots_path')
        self.ytick_distance = self.get('ytick_distance', default=200)
        self.min_dus = self.get('min_dus', default=1)
        self.min_doms = self.get('min_doms', default=4)
        self.det_id = self.require('det_id')
        self.event_selection_table = self.get('event_selection_table',
                                              default='event_selection')
        self.logbook = self.get('logbook', default="Individual+Logbooks")
        self.t0set = None
        self.calib = None
        self.max_z = None
        self.last_plot_time = 0
        self.lower_limits = {}

        self.sds = kp.db.StreamDS()

        self.index = 0

    def prepare(self):
        if not self.services["table_exists"](self.event_selection_table):
            self.services["create_table"](self.event_selection_table, [
                "overlays", "n_hits", "n_triggered_hits", "n_dus",
                "plot_filename", "run_id", "det_id", "frame_index",
                "trigger_counter", "utc_timestamp"
            ], [
                "INT", "INT", "INT", "INT", "TEXT", "INT", "INT", "INT", "INT",
                "INT"
            ])

        self._update_calibration()
        self._update_lower_limits()

        self.run = True
        self.max_queue = 300
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self.plot, daemon=True)
        self.thread.start()

    def _update_lower_limits(self):
        """Update the lower limits for the Top-10 candidate selection"""
        n_candidates = 10
        for category in ["overlays", "n_hits", "n_triggered_hits"]:
            lower_limit = self.services["query"](
                "SELECT {cat} FROM {tab} ORDER BY {cat} DESC LIMIT {limit}".
                format(cat=category,
                       tab=self.event_selection_table,
                       limit=n_candidates))[-1][0]
            self.lower_limits[category] = lower_limit

        self.cprint("Current limits for the Top-10: {}".format(
            self.lower_limits))

    def _update_calibration(self):
        self.cprint("Updating calibration")
        try:
            self.t0set = self.sds.t0sets(
                detid=self.det_id).iloc[-1]['CALIBSETID']
            self.calib = kp.calib.Calibration(det_id=self.det_id,
                                              t0set=self.t0set)
        except URLError as e:
            self.log.error(
                "Unable to update calibration, no connection to the DB.\n{}".
                format(e))
        else:
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

        n_triggered_dus = len(np.unique(hits[hits.triggered == True].du))
        n_triggered_doms = len(np.unique(hits[hits.triggered == True].dom_id))
        if n_triggered_dus < self.min_dus or n_triggered_doms < self.min_doms:
            self.log.debug(f"Skipping event with {n_triggered_dus} DUs "
                           f"and {n_triggered_doms} DOMs.")
            return blob

        # print("Event queue size: {0}".format(self.queue.qsize()))
        if self.queue.qsize() < self.max_queue:
            raw_data = blob["CHData"]
            self.queue.put((event_info, hits, raw_data))
        else:
            self.cprint("Skipping, queue is full...")

        return blob

    def plot(self):
        while self.run:
            try:
                event_info, hits, raw_data = self.queue.get(timeout=50)
            except queue.Empty:
                continue
            with lock:
                self.create_plot(event_info, hits, raw_data)

    def create_plot(self, event_info, hits, raw_data):

        trigger_mask = event_info.trigger_mask[0]
        det_id = event_info.det_id[0]
        run_id = event_info.run_id[0]
        frame_index = event_info.frame_index[0]
        trigger_counter = event_info.trigger_counter[0]
        utc_timestamp = event_info.utc_seconds[0]
        overlays = event_info.overlays[0]
        n_hits = len(hits)
        n_triggered_hits = sum(hits.triggered)

        # Check for new record
        is_in_top10 = overlays > self.lower_limits[
            'overlays'] or n_hits > self.lower_limits[
                'n_hits'] or n_triggered_hits > self.lower_limits[
                    "n_triggered_hits"]

        if (utc_timestamp - self.last_plot_time) < 60 and not is_in_top10:
            self.log.debug("Skipping plot...")
            return

        self.cprint(self.__class__.__name__ + ": updating plot.")

        dus = set(hits.du)
        n_dus = len(dus)

        grid_lines = self.calib.detector.pmts.pos_z[
            (self.calib.detector.pmts.du == min(dus))
            & (self.calib.detector.pmts.channel_id == 0)]

        trigger_params = ' '.join([
            trig
            for trig, trig_check in (("MX", is_mxshower), ("3DM", is_3dmuon),
                                     ("3DS", is_3dshower))
            if trig_check(int(trigger_mask))
        ])

        title = "z-t-Plot for DetID-{0} (t0set: {1}), Run {2}, "  \
                "FrameIndex {3}, TriggerCounter {4}, Overlays {5}, "  \
                "Trigger: {6}\n{7} UTC".format(
                    det_id, self.t0set, run_id, frame_index, trigger_counter,
                    overlays, trigger_params,
                    datetime.utcfromtimestamp(event_info.utc_seconds))

        filename = 'ztplot'
        f = os.path.join(self.plots_path, filename + '.png')
        f_tmp = os.path.join(self.plots_path, filename + '_tmp.png')

        fig = ztplot(hits,
                     filename=f_tmp,
                     title=title,
                     max_z=self.max_z,
                     ytick_distance=self.ytick_distance,
                     grid_lines=grid_lines)
        shutil.move(f_tmp, f)

        if is_in_top10:
            self.cprint(
                "New record! Overlays: {}, hits: {}, triggered hits: {}".
                format(overlays, n_hits, n_triggered_hits))

            base_filename = os.path.join(
                self.plots_path,
                "event_selection/ztplot_{:08d}_{:08d}_FI{}_TC{}".format(
                    det_id, run_id, frame_index, trigger_counter))
            plot_filename = base_filename + ".png"
            rawdata_filename = base_filename + ".dat"

            self.services["insert_row"](self.event_selection_table, [
                "overlays", "n_hits", "n_triggered_hits", "n_dus",
                "plot_filename", "run_id", "det_id", "frame_index",
                "trigger_counter", "utc_timestamp"
            ], [
                overlays, n_hits, n_triggered_hits, n_dus, plot_filename,
                run_id, det_id, frame_index, trigger_counter, utc_timestamp
            ])
            shutil.copy(f, plot_filename)

            with open(rawdata_filename, "wb") as fobj:
                fobj.write(raw_data)

            self._update_lower_limits()
            self.services['post_elog'](
                logbook=self.logbook,
                subject="New massive event!",
                message="A new event has made it into the top 10!",
                message_type="Monitoring",
                author="Gal T",
                files=[plot_filename])

        plt.close(fig)
        plt.close('all')
        self.last_plot_time = utc_timestamp

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
    pipe.attach(LocalDBService, thread_safety=False)
    pipe.attach(ELOGService)
    pipe.attach(kp.io.ch.CHPump,
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
