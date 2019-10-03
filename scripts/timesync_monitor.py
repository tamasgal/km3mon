#!/usr/bin/env python
# coding=utf-8
# Filename: timesync_monitor.py
# Author: Tamas Gal <tgal@km3net.de>
# vim: ts=4 sw=4 et
"""
Monitors the time sync of DOMs using the MSG of the CLB DOM STATUS 1 field
from the supernova timeslice stream (IO_TSSN).

Usage:
    timesync_monitor.py [options]
    timesync_monitor.py (-h | --help)

Options:
    -l LIGIER_IP            The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT          The port of the ligier [default: 5553].
    -m LOGGING_LIGIER_IP    The IP of the logging ligier [default: 127.0.0.1].
    -q LOGGING_LIGIER_PORT  The port of the logging ligier [default: 5553].
    -h --help               Show this screen.

"""
import datetime
import km3pipe as kp


class TimeSyncChecker(kp.Module):
    def configure(self):
        logging_ligier = self.require("logging_ligier_ip")
        logging_ligier_port = self.require("logging_ligier_port")
        self.ch_client = kp.controlhost.Client(logging_ligier,
                                               port=logging_ligier_port)
        self.alert = kp.time.Cuckoo(interval=10, callback=self._alert)

    def _alert(self, msg):
        date = datetime.datetime.utcnow().strftime("%c")
        msg = f"ALERT (MONITORING) {date}: {msg}"
        print(msg)
        self.ch_client.put_message("MSG", msg)

    def process(self, blob):
        dom_ids_invalid = []
        dom_ids_valid = []
        for dom_id, frameinfo in blob['TimesliceFrameInfos'].items():
            valid_time_sync = bool(frameinfo.dom_status[0] & (1 << (32 - 1)))
            if not valid_time_sync:
                dom_ids_invalid.append(dom_id)
            else:
                dom_ids_valid.append(dom_id)
        if dom_ids_invalid:
            self.alert("invalid time sync for DOM ID: {} /// valid: {}".format(
                ','.join(map(str, dom_ids_invalid)),
                ','.join(map(str, dom_ids_valid))))
        return blob

    def finish(self):
        self.ch_client._disconnect()


def main():
    from docopt import docopt
    args = docopt(__doc__)

    ligier_ip = args['-l']
    ligier_port = int(args['-p'])
    logging_ligier_ip = args['-m']
    logging_ligier_port = int(args['-q'])

    pipe = kp.Pipeline()
    pipe.attach(kp.io.ch.CHPump,
                host=ligier_ip,
                port=ligier_port,
                tags="IO_TSSN")
    pipe.attach(kp.io.daq.TimesliceParser)
    pipe.attach(TimeSyncChecker,
                logging_ligier_ip=logging_ligier_ip,
                logging_ligier_port=logging_ligier_port)
    pipe.drain()


if __name__ == '__main__':
    main()
