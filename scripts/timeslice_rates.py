#!/usr/bin/env python
# coding=utf-8
# Filename: timeslice_rates.py
# Author: Tamas Gal <tgal@km3net.de>
# vim: ts=4 sw=4 et
"""
Monitors timeslice rates.

Usage:
    timeslice_rates.py [options]
    timeslice_rates.py (-h | --help)

Options:
    -l LIGIER_IP    The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT  The port of the ligier [default: 5553].
    -o PLOT_DIR     The directory to save the plot [default: plots].
    -h --help       Show this screen.

"""
from __future__ import division, print_function

from datetime import datetime
from collections import defaultdict, deque, OrderedDict
from itertools import chain
import sys
from io import BytesIO
from os.path import join
from struct import unpack
import shutil
import time
import threading

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as md

import km3pipe as kp
from km3pipe.io.daq import DAQPreamble
import km3pipe.style

VERSION = "1.0"
km3pipe.style.use('km3pipe')


class TimesliceRate(kp.Module):
    def configure(self):
        self.plots_path = self.require('plots_path')
        self.interval = self.get( "interval", default=10)
        self.filename = self.get("filename", default="timeslice_rates")
        self.with_minor_ticks = self.get("with_minor_ticks", default=False)
        print("Update interval: {}s".format(self.interval))
        self.timeslice_counts = defaultdict(int)
        self.timeslice_rates = OrderedDict()

        self.styles = {
            "xfmt":
            md.DateFormatter('%Y-%m-%d %H:%M'),
            "general":
            dict(markersize=6, linestyle='None'),
            "L0":
            dict(
                marker='D',
                markerfacecolor='None',
                markeredgecolor='tomato',
                markeredgewidth=1),
            "L1":
            dict(marker='X', markerfacecolor='dodgerblue'),
            "L2":
            dict(marker='v', markerfacecolor='orange'),
            "SN":
            dict(marker='^', markerfacecolor='olivedrab'),
        }

        queue_len = int(60 * 24 / (self.interval / 60))
        for ts_type in ["L0", "L1", "L2", "SN"]:
            self.timeslice_rates[ts_type] = deque(maxlen=queue_len)

        self.run = True
        self.thread = threading.Thread(target=self.plot).start()
        self.lock = threading.Lock()

        self.run_changes = []
        self.current_run_id = 0
        self.det_id = 0

    def process(self, blob):
        print("Process")
        ts_type = str(blob['CHPrefix'].tag).split("IO_TS")[1]
        sys.stdout.write('.')
        sys.stdout.flush()

        data = blob['CHData']
        data_io = BytesIO(data)
        tsl_size, datatype = unpack('<ii', data_io.read(8))
        det_id, run, sqnr = unpack('<iii', data_io.read(12))

        self.det_id = det_id
        if run > self.current_run_id:
            self.current_run_id = run
            self._log_run_change()
        with self.lock:
            self.timeslice_counts[ts_type] += 1

        print(self.timeslice_counts)

        return blob

    def _log_run_change(self):
        self.print("New run: %s" % self.current_run_id)
        now = datetime.utcnow()
        self.run_changes.append((now, self.current_run_id))

    def _get_run_changes_to_plot(self):
        self.print("Checking run changes out of range")
        overall_rates = self.timeslice_rates['SN']
        # if not overall_rates:
        #     self.print("No timeslice rates logged  yet, nothing to remove.")
        #     return
        self.print("  all:     {}".format(self.run_changes))
        run_changes_to_plot = []
        min_timestamp = min(overall_rates)[0]
        self.print("  earliest timestamp to plot: {}".format(min_timestamp))
        for timestamp, run in self.run_changes:
            if timestamp > min_timestamp:
                run_changes_to_plot.append((timestamp, run))
        self.print("  to plot: {}".format(run_changes_to_plot))
        return run_changes_to_plot

    def plot(self):
        while self.run:
            time.sleep(self.interval)
            self.create_plot()

    def create_plot(self):
        print('\n' + self.__class__.__name__ + ": updating plot.")

        timestamp = datetime.utcnow()

        with self.lock:
            for ts_type, n_events in self.timeslice_counts.items():
                timeslice_rate = n_events / self.interval
                self.timeslice_rates[ts_type].append((timestamp, timeslice_rate))
            self.timeslice_counts = defaultdict(int)

        fig, ax = plt.subplots(figsize=(16, 4))

        for ts_type, rates in self.timeslice_rates.items():
            if not rates:
                self.log.warning("Empty rates, skipping...")
                continue
            timestamps, timeslice_rates = zip(*rates)
            ax.plot(
                timestamps,
                timeslice_rates,
                **self.styles[ts_type],
                **self.styles['general'],
                label=ts_type)

        run_changes_to_plot = self._get_run_changes_to_plot()
        if run_changes_to_plot:
            self.log.critical("No run changes!")
            self.print("Recorded run changes: {}".format(run_changes_to_plot))
            all_rates = [r for d, r in chain(*self.timeslice_rates.values())]
            if not all_rates:
                self.log.warning("Empty rates, skipping...")
                return
            min_timeslice_rate = min(all_rates)
            max_timeslice_rate = max(all_rates)
            for run_start, run in run_changes_to_plot:
                plt.text(
                    run_start, (min_timeslice_rate + max_timeslice_rate) / 2,
                    "\nRUN %s  " % run,
                    rotation=60,
                    verticalalignment='top',
                    fontsize=8,
                    color='gray')
                ax.axvline(
                    run_start, color='#ff0f5b', linestyle='--', alpha=0.8)  # added

        ax.set_title("Timeslice Rates for DetID-{0}\n{1} UTC".format(
            self.det_id,
            datetime.utcnow().strftime("%c")))
        ax.set_xlabel("time")
        ax.set_ylabel("timeslice rate [Hz]")
        ax.xaxis.set_major_formatter(self.styles["xfmt"])
        ax.grid(True, which='minor')
        if self.with_minor_ticks:
            ax.minorticks_on()
        plt.legend()

        fig.tight_layout()

        filename = join(self.plots_path, self.filename + '_lin.png')
        filename_tmp = join(self.plots_path, self.filename + '_lin_tmp.png')
        plt.savefig(filename_tmp, dpi=120, bbox_inches="tight")
        shutil.move(filename_tmp, filename)

        try:
            ax.set_yscale('log')
        except ValueError:
            pass

        filename = join(self.plots_path, self.filename + '.png')
        filename_tmp = join(self.plots_path, self.filename + '_tmp.png')
        plt.savefig(filename_tmp, dpi=120, bbox_inches="tight")
        shutil.move(filename_tmp, filename)

        plt.close('all')
        print("Plot updated at '{}'.".format(filename))

    def finish(self):
        self.run = False
        if self.thread is not None:
            self.thread.stop()


def main():
    from docopt import docopt
    args = docopt(__doc__, version=VERSION)

    plots_path = args['-o']
    ligier_ip = args['-l']
    ligier_port = int(args['-p'])

    pipe = kp.Pipeline()
    pipe.attach(
        kp.io.ch.CHPump,
        host=ligier_ip,
        port=ligier_port,
        tags='IO_TSL0,IO_TSL1,IO_TSL2,IO_TSSN',
        timeout=60 * 60 * 24 * 7,
        max_queue=200000)
    pipe.attach(TimesliceRate, interval=10, plots_path=plots_path)
    pipe.drain()


if __name__ == '__main__':
    main()
