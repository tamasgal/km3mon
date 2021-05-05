#!/usr/bin/env python
# coding=utf-8
# vim: ts=4 sw=4 et
"""
=========================
K40 Intra-DOM Calibration
=========================

Usage:
    k40_calibration.py [options]
    k40_calibration.py (-h | --help)

Options:
    -l LIGIER_IP    The IP of the ligier [default: 127.0.0.1].
    -p LIGIER_PORT  The port of the ligier [default: 5553].
    -d DET_ID       Detector ID.
    -o PLOT_DIR     The directory to save the plot [default: /plots].
    -h --help       Show this screen.

"""
# Author: Jonas Reubelt <jreubelt@km3net.de> and Tamas Gal <tgal@km3net.de>
# License: MIT
import os
import km3pipe as kp
import km3pipe.style
from km3modules import k40
from km3modules.common import StatusBar, MemoryObserver, Siphon
from km3modules.plot import IntraDOMCalibrationPlotter

km3pipe.style.use('km3pipe')


def main():
    from docopt import docopt
    args = docopt(__doc__)

    det_id = int(args['-d'])
    plots_path = args['-o']
    ligier_ip = args['-l']
    ligier_port = int(args['-p'])

    det_oid = kp.db.DBManager().get_det_oid(det_id)

    pipe = kp.Pipeline(timeit=True)
    pipe.attach(
        kp.io.ch.CHPump,
        host=ligier_ip,
        port=ligier_port,
        tags='IO_TSL1, IO_MONIT',
        timeout=7 * 60 * 60 * 24,
        max_queue=200000)
    pipe.attach(kp.io.ch.CHTagger)
    pipe.attach(StatusBar, every=50000)
    pipe.attach(MemoryObserver, every=100000)
    pipe.attach(k40.MedianPMTRatesService, only_if='IO_MONIT')
    pipe.attach(kp.io.daq.TimesliceParser)
    pipe.attach(
        k40.TwofoldCounter,
        tmax=10,
        dump_filename=os.path.join(plots_path, 'twofold_counts.p'))
    pipe.attach(Siphon, volume=10 * 60 * 180, flush=True)
    pipe.attach(k40.K40BackgroundSubtractor)
    pipe.attach(k40.IntraDOMCalibrator, ctmin=-1, det_id=det_id)
    pipe.attach(
        IntraDOMCalibrationPlotter,
        det_oid=det_oid,
        data_path=plots_path,
        plots_path=plots_path)
    pipe.attach(k40.ResetTwofoldCounts)
    pipe.drain()


if __name__ == '__main__':
    main()
