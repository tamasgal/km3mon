#!/usr/bin/env python
# coding=utf-8
# Filename: trigger_rates.py
# Author: Tamas Gal <tgal@km3net.de>
# vim: ts=4 sw=4 et
"""
Monitors trigger rates.

Usage:
    trigger_rates.py [options]
    trigger_rates.py (-h | --help)

Options:
    -l LIGIER_IP    The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT  The port of the ligier [default: 5553].
    -o PLOT_DIR     The directory to save the plot [default: plots].
    -h --help       Show this screen.

"""
from __future__ import division, print_function

from datetime import datetime
from collections import defaultdict, deque, OrderedDict
import sys
from io import BytesIO
from os.path import join
import shutil
import time
import threading

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as md

import km3pipe as kp
from km3pipe.config import Config
from km3pipe.io.daq import (DAQPreamble, DAQEvent, is_3dshower, is_3dmuon,
                            is_mxshower)
import km3pipe.style

VERSION = "1.0"
km3pipe.style.use('km3pipe')


class TriggerRate(kp.Module):
    def configure(self):
        self.plots_path = self.require('plots_path')
        self.interval = self.get(
            "interval", default=self.trigger_rate_sampling_period())
        self.filename = self.get("filename", default="trigger_rates")
        self.with_minor_ticks = self.get("with_minor_ticks", default=False)
        print("Update interval: {}s".format(self.interval))
        self.trigger_counts = defaultdict(int)
        self.trigger_rates = OrderedDict()

        self.styles = {
            "xfmt":
            md.DateFormatter('%Y-%m-%d %H:%M'),
            "general":
            dict(markersize=6, linestyle='None'),
            "Overall":
            dict(
                marker='D',
                markerfacecolor='None',
                markeredgecolor='tomato',
                markeredgewidth=1),
            "3DMuon":
            dict(marker='X', markerfacecolor='dodgerblue'),
            "MXShower":
            dict(marker='v', markerfacecolor='orange'),
            "3DShower":
            dict(marker='^', markerfacecolor='olivedrab'),
        }

        queue_len = int(60 * 24 / (self.interval / 60))
        for trigger in ["Overall", "3DMuon", "MXShower", "3DShower"]:
            self.trigger_rates[trigger] = deque(maxlen=queue_len)

        self.run = True
        self.thread = threading.Thread(target=self.plot).start()
        self.lock = threading.Lock()

        self.run_changes = []
        self.current_run_id = 0

    def process(self, blob):
        if not str(blob['CHPrefix'].tag) == 'IO_EVT':
            return blob
        sys.stdout.write('.')
        sys.stdout.flush()

        data = blob['CHData']
        data_io = BytesIO(data)
        preamble = DAQPreamble(file_obj=data_io)  # noqa
        event = DAQEvent(file_obj=data_io)
        if event.header.run > self.current_run_id:
            self.current_run_id = event.header.run
            self._log_run_change()
        tm = event.trigger_mask
        with self.lock:
            self.trigger_counts["Overall"] += 1
            self.trigger_counts["3DShower"] += is_3dshower(tm)
            self.trigger_counts["MXShower"] += is_mxshower(tm)
            self.trigger_counts["3DMuon"] += is_3dmuon(tm)

        print(self.trigger_counts)

        return blob

    def _log_run_change(self):
        self.print("New run: %s" % self.current_run_id)
        now = datetime.utcnow()
        self.run_changes.append((now, self.current_run_id))

    def _get_run_changes_to_plot(self):
        self.print("Checking run changes out of range")
        overall_rates = self.trigger_rates['Overall']
        if not overall_rates:
            self.print("No trigger rates logged  yet, nothing to remove.")
            return
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
            for trigger, n_events in self.trigger_counts.items():
                trigger_rate = n_events / self.interval
                self.trigger_rates[trigger].append((timestamp, trigger_rate))
            self.trigger_counts = defaultdict(int)

        fig, ax = plt.subplots(figsize=(16, 4))

        for trigger, rates in self.trigger_rates.items():
            if not rates:
                self.log.warning("Empty rates, skipping...")
                continue
            timestamps, trigger_rates = zip(*rates)
            ax.plot(
                timestamps,
                trigger_rates,
                **self.styles[trigger],
                **self.styles['general'],
                label=trigger)

        run_changes_to_plot = self._get_run_changes_to_plot()
        self.print("Recorded run changes: {}".format(run_changes_to_plot))
        min_trigger_rate = min(
            [r[1] for r in trigger_rates['Overall'].values()])
        for run_start, run in run_changes_to_plot:
            plt.text(
                run_start,
                min_trigger_rate,
                "\nRUN %s  " % run,
                rotation=90,
                verticalalignment='top',
                fontsize=8,
                color='gray')
            ax.axvline(
                run_start, color='#ff0f5b', linestyle='--', alpha=0.8)  # added

        ax.set_title("Trigger Rates\n{0} UTC".format(
            datetime.utcnow().strftime("%c")))
        ax.set_xlabel("time")
        ax.set_ylabel("trigger rate [Hz]")
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

    def trigger_rate_sampling_period(self):
        try:
            return int(Config().get("Monitoring",
                                    "trigger_rate_sampling_period"))
        except (TypeError, ValueError):
            return 180

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
        tags='IO_EVT',
        timeout=60 * 60 * 24 * 7,
        max_queue=200000)
    pipe.attach(TriggerRate, interval=300, plots_path=plots_path)
    pipe.drain()


if __name__ == '__main__':
    main()
