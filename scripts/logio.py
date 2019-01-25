#!/usr/bin/env python
# coding=utf-8
# Filename: logio.py
# Author: Tamas Gal <tgal@km3net.de>
# vim: ts=4 sw=4 et
"""
Sends MSG data from Ligier to a log.io server to be displayed in real-time.

Usage:
    event_hits.py [options]
    event_hits.py (-h | --help)

Options:
    -l LIGIER_IP    The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT  The port of the ligier [default: 5553].
    -x LOGIO_IP    The IP of the ligier [default: 127.0.0.1].
    -q LOGIO_PORT  The port of the ligier [default: 28777].
    -h --help       Show this screen.

"""
import socket
import time

from km3pipe import Pipeline, Module
from km3pipe.io import CHPump


class LogIO(Module):
    def configure(self):
        url = self.get('logio_ip', default='127.0.0.1')
        port = self.get('logio_port', default=28777)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((url, port))

    def process(self, blob):
        data = blob['CHData']
        log_level = 'info'
        if "ERROR" in data:
            log_level = 'error'
        if "WARNING" in data:
            log_level = 'warning'
        source = "Other"
        if " F0" in data:
            source = "DataFilter"
        if " Q0" in data:
            source = "DataQueue"
        if " W0" in data:
            source = "DataWriter"
        self.sock.send("+log|{0}|Portopalo DAQ|{1}|{2}\r\n".format(
            source, log_level, data))
        return blob

    def finish(self):
        self.sock.close()


def main():
    from docopt import docopt
    args = docopt(__doc__)

    ligier_ip = args['-l']
    ligier_port = int(args['-p'])
    logio_ip = args['-x']
    logio_port = int(args['-q'])

    pipe = Pipeline()
    pipe.attach(
        CHPump,
        host=ligier_ip,
        port=ligier_port,
        tags='MSG',
        timeout=7 * 60 * 60 * 24,
        max_queue=500)
    pipe.attach(LogIO, logio_ip=logio_ip, logio_port=logio_port)
    pipe.drain()


if __name__ == '__main__':
    main()
