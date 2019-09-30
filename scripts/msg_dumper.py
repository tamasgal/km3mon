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
    -o LOG_DIR      Directory to dump the messages [default: logs].
    -x PREFIX       Prefix for the log files [default: MSG].
    -h --help       Show this screen.

"""
import datetime
import os
from shutil import copyfile

from km3pipe import Pipeline, Module
from km3pipe.io import CHPump


def current_date_str(fmt="%Y-%m-%d"):
    """Return the current datetime string"""
    return datetime.datetime.utcnow().strftime(fmt)


class MSGDumper(Module):
    def configure(self):
        self.path = os.path.abspath(self.require('path'))
        self.prefix = self.require('prefix')
        self.current_date = current_date_str()
        self.filename = self.prefix + ".log"
        self.filepath = os.path.join(self.path, self.filename)
        self.fobj = open(self.filepath, 'a')

    def update_file_descriptor(self):
        current_date = current_date_str()
        if self.current_date != current_date:
            archived_name = "{}_{}.log".format(self.prefix, self.current_date)
            self.print("Cycling the log file: {} -> {}".format(
                self.filename, archived_name))
            copyfile(self.filepath, os.path.join(self.path, archived_name))
            self.fobj.close()
            self.fobj = open(self.filepath, 'w')
            self.current_date = current_date

    def process(self, blob):
        data = blob['CHData'].decode()
        source = "Other"
        if " A0" in data:
            source = "AcousticDataFilter"
        if " F0" in data:
            source = "DataFilter"
        if " Q0" in data:
            source = "DataQueue"
        if " W0" in data:
            source = "DataWriter"

        entry = "{} [{}]: {}\n".format(self.filename, source, data)
        self.update_file_descriptor()
        self.fobj.write(entry)
        self.fobj.flush()
        return blob

    def finish(self):
        if self.fobj is not None:
            self.fobj.close()


def main():
    from docopt import docopt
    args = docopt(__doc__)

    ligier_ip = args['-l']
    ligier_port = int(args['-p'])
    path = args['-o']
    prefix = args['-x']

    pipe = Pipeline()
    pipe.attach(CHPump,
                host=ligier_ip,
                port=ligier_port,
                tags='MSG',
                timeout=7 * 60 * 60 * 24,
                max_queue=500)
    pipe.attach(MSGDumper, prefix=prefix, path=path)
    pipe.drain()


if __name__ == '__main__':
    main()
