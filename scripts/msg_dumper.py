#!/usr/bin/env python
# coding=utf-8
# Filename: msg_dumper.py
# Author: Tamas Gal <tgal@km3net.de>
# vim: ts=4 sw=4 et
"""
Dumps MSG data from Ligier to a file.

Usage:
    msg_dumper.py [options]
    msg_dumper.py (-h | --help)

Options:
    -l LIGIER_IP    The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT  The port of the ligier [default: 5553].
    -f LOG_FILE     Log file to dump the messages [default: MSG.log].
    -h --help       Show this screen.

"""
import os
import time

from km3pipe import Pipeline, Module
from km3pipe.io import CHPump


class MSGDumper(Module):
    def configure(self):
        self.filename = self.get('filename', default='MSG.log')
        self.fobj = open(os.path.abspath(self.filename), 'a')

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

        entry = "{} [{}] - {}: {}\n".format(self.filename, source, log_level,
                                            data)
        self.fobj.write(entry)
        return blob

    def finish(self):
        self.fobj.close()


def main():
    from docopt import docopt
    args = docopt(__doc__)

    ligier_ip = args['-l']
    ligier_port = int(args['-p'])
    filename = args['-f']

    pipe = Pipeline()
    pipe.attach(
        CHPump,
        host=ligier_ip,
        port=ligier_port,
        tags='MSG',
        timeout=7 * 60 * 60 * 24,
        max_queue=500)
    pipe.attach(MSGDumper, filename=filename)
    pipe.drain()


if __name__ == '__main__':
    main()
