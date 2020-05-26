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
from itertools import chain
from functools import partial
import sys
from io import BytesIO
from os.path import join, exists
import shutil
import struct
import time
import threading

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as md

import toml

from rocketchat_API.rocketchat import RocketChat

import km3pipe as kp
from km3pipe.config import Config
from km3pipe.io.daq import (DAQPreamble, DAQEvent, is_3dshower, is_3dmuon,
                            is_mxshower)
import km3pipe.style

VERSION = "1.0"
km3pipe.style.use('km3pipe')

URL = "https://chat.km3net.de"
CONFIG = "pipeline.toml"

with open(CONFIG, 'r') as fobj:
    config = toml.load(fobj)
    BOTNAME = config['Alerts']['botname']
    PASSWORD = config['Alerts']['password']
    CHANNEL = config['Alerts']['channel']

rocket = RocketChat(BOTNAME, PASSWORD, server_url=URL)


def sendchatalert(msg):
    with open(CONFIG, 'r') as fobj:
        shifters = toml.load(fobj)['Alerts'].get('shifters', "shifters")
    rocket.chat_post_message(shifters + ": " + msg, channel=CHANNEL)


class TriggerRate(kp.Module):
    """Trigger rate plotter"""
    def configure(self):
        self.plots_path = self.require('plots_path')
        self.data_path = self.get('data_path', default='data')
        self.interval = self.get("interval",
                                 default=self.trigger_rate_sampling_period())
        self.filename = self.get("filename", default="trigger_rates")
        self.with_minor_ticks = self.get("with_minor_ticks", default=False)

        self.sendmail = kp.time.Cuckoo(
            15 * 60, partial(kp.tools.sendmail, "orca.alerts@km3net.de"))
        self.sendchatalert = kp.time.Cuckoo(30 * 60, sendchatalert)

        print("Update interval: {}s".format(self.interval))
        self.trigger_counts = defaultdict(int)
        self.trigger_rates = OrderedDict()
        self._trigger_types = ["Overall", "3DMuon", "MXShower", "3DShower"]
        self.trigger_rates_fobj = None

        self.initialise_data_logging()

        self.styles = {
            "xfmt": md.DateFormatter('%Y-%m-%d %H:%M'),
            "general": dict(markersize=6, linestyle=':', linewidth=1),
            "Overall": dict(marker='D', color='tomato', markeredgewidth=1),
            "3DMuon": dict(marker='X', color='dodgerblue'),
            "MXShower": dict(marker='v', color='orange'),
            "3DShower": dict(marker='^', color='olivedrab'),
        }

        queue_len = int(60 * 24 / (self.interval / 60))
        for trigger in self._trigger_types:
            self.trigger_rates[trigger] = deque(maxlen=queue_len)

        self.run = True
        threading.Thread(target=self.plot).start()
        self.lock = threading.Lock()

        self.run_changes = []
        self.current_run_id = 0
        self.det_id = 0

    def initialise_data_logging(self):
        """Set up a CSV to store the trigger rate data"""
        filename = join(self.data_path, "trigger_rates.csv")
        if not exists(filename):
            self.trigger_rates_fobj = open(filename, "w")
            self.trigger_rates_fobj.write('timestamp,' +
                                          ','.join(self._trigger_types) + '\n')
        else:
            self.trigger_rates_fobj = open(filename, "a")
        self.trigger_rates_fobj.flush()

    def process(self, blob):
        """Analyse the trigger flags for an incoming event"""
        if not str(blob['CHPrefix'].tag) == 'IO_EVT':
            return blob
        sys.stdout.write('.')
        sys.stdout.flush()

        data = blob['CHData']
        data_io = BytesIO(data)
        try:
            preamble = DAQPreamble(file_obj=data_io)  # noqa
            event = DAQEvent(file_obj=data_io)
        except struct.error:
            self.log.error("Corrupt event data recieved, skipping...")
            return
        self.det_id = event.header.det_id
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
        """Keep track of a run change"""
        self.print("New run: %s" % self.current_run_id)
        now = datetime.utcnow()
        self.run_changes.append((now, self.current_run_id))

    def _get_run_changes_to_plot(self):
        """Retrieve all run numbers to be plotted on the trigger rate plot"""
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
        """The plot loop, calling the plotter every `self.interval` seconds."""
        while self.run:
            time.sleep(self.interval)
            timestamp, trigger_rates = self.calculate_trigger_rates()
            self.write_trigger_rates(timestamp, trigger_rates)
            self.create_plot()

    def write_trigger_rates(self, timestamp, trigger_rates):
        """Write the trigger rate information to the CSV file"""
        entry = f"{timestamp}"
        for trigger_type in self._trigger_types:
            try:
                trigger_rate = trigger_rates[trigger_type]
            except KeyError:
                trigger_rate = 0
            if trigger_rate == 0:
                self.sendmail("Subject: Trigger rate is 0Hz!\n\n")
                self.sendchatalert("Trigger rate is 0Hz!")
            entry += f",{trigger_rate}"
        entry += '\n'
        self.trigger_rates_fobj.write(entry)
        self.trigger_rates_fobj.flush()

    def calculate_trigger_rates(self):
        """Calculate the trigger rates from the event trigger parameters"""
        timestamp = datetime.utcnow()
        trigger_rates = {}
        with self.lock:
            for trigger, n_events in self.trigger_counts.items():
                trigger_rate = n_events / self.interval
                self.trigger_rates[trigger].append((timestamp, trigger_rate))
                trigger_rates[trigger] = trigger_rate
            self.trigger_counts = defaultdict(int)
        return timestamp.timestamp(), trigger_rates

    def create_plot(self):
        """Create the trigger rate plot"""
        print('\n' + self.__class__.__name__ + ": updating plot.")

        fig, ax = plt.subplots(figsize=(16, 4))

        for trigger, rates in self.trigger_rates.items():
            if not rates:
                self.log.warning("Empty rates, skipping...")
                continue
            timestamps, trigger_rates = zip(*rates)
            ax.plot(timestamps,
                    trigger_rates,
                    **self.styles[trigger],
                    **self.styles['general'],
                    label=trigger)

        run_changes_to_plot = self._get_run_changes_to_plot()
        self.print("Recorded run changes: {}".format(run_changes_to_plot))
        all_rates = [r for d, r in chain(*self.trigger_rates.values())]
        if not all_rates:
            self.log.warning("Empty rates, skipping...")
            return
        min_trigger_rate = min(all_rates)
        max_trigger_rate = max(all_rates)
        for run_start, run in run_changes_to_plot:
            plt.text(run_start, (min_trigger_rate + max_trigger_rate) / 2,
                     "\nRUN %s  " % run,
                     rotation=60,
                     verticalalignment='top',
                     fontsize=8,
                     color='gray')
            ax.axvline(run_start, color='#ff0f5b', linestyle='--',
                       alpha=0.8)  # added

        ax.set_title("Trigger Rates for DetID-{0}\n{1} UTC".format(
            self.det_id,
            datetime.utcnow().strftime("%c")))
        ax.set_ylabel("trigger rate [Hz]")
        ax.xaxis.set_major_formatter(self.styles["xfmt"])
        ax.grid(True, which='minor')
        ax.tick_params(labelright=True, which="both")
        if self.with_minor_ticks:
            ax.minorticks_on()
        plt.legend()

        fig.tight_layout()

        filename = join(self.plots_path, self.filename + '_lin.png')
        filename_tmp = join(self.plots_path, self.filename + '_lin_tmp.png')
        fig.savefig(filename_tmp, dpi=120, bbox_inches="tight")
        shutil.move(filename_tmp, filename)

        try:
            ax.set_yscale('log')
        except ValueError:
            pass

        filename = join(self.plots_path, self.filename + '.png')
        filename_tmp = join(self.plots_path, self.filename + '_tmp.png')
        fig.savefig(filename_tmp, dpi=120, bbox_inches="tight")
        shutil.move(filename_tmp, filename)

        plt.close('all')
        print("Plot updated at '{}'.".format(filename))

    def trigger_rate_sampling_period(self):
        """This is obsolete and will be removed"""
        try:
            return int(Config().get("Monitoring",
                                    "trigger_rate_sampling_period"))
        except (TypeError, ValueError):
            return 180

    def finish(self):
        self.trigger_rates_fobj.close()
        self.run = False


def main():
    from docopt import docopt
    args = docopt(__doc__, version=VERSION)

    plots_path = args['-o']
    ligier_ip = args['-l']
    ligier_port = int(args['-p'])

    pipe = kp.Pipeline()
    pipe.attach(kp.io.ch.CHPump,
                host=ligier_ip,
                port=ligier_port,
                tags='IO_EVT',
                timeout=60 * 60 * 24 * 7,
                max_queue=200000)
    pipe.attach(TriggerRate, interval=300, plots_path=plots_path)
    pipe.drain()


if __name__ == '__main__':
    main()
