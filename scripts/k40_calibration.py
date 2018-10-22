#!/usr/bin/env python
# coding=utf-8
# vim: ts=4 sw=4 et
"""
=========================
K40 Intra-DOM Calibration
=========================

The following script calculates the PMT time offsets using K40 coincidences

"""
# Author: Jonas Reubelt <jreubelt@km3net.de> and Tamas Gal <tgal@km3net.de>
# License: MIT
import km3pipe as kp
import km3pipe.style
from km3modules import k40
from km3modules.common import StatusBar, MemoryObserver, Siphon
from km3modules.plot import IntraDOMCalibrationPlotter

km3pipe.style.use('km3pipe')

DET_ID = 39

pipe = kp.Pipeline(timeit=True)
pipe.attach(
    kp.io.ch.CHPump,
    host='127.0.0.1',
    port=6001,
    tags='IO_TSL1, IO_MONIT',
    timeout=7 * 60 * 60 * 24,
    max_queue=200000)
pipe.attach(kp.io.ch.CHTagger)
pipe.attach(StatusBar, every=50000)
pipe.attach(MemoryObserver, every=100000)
pipe.attach(k40.MedianPMTRatesService, only_if='IO_MONIT')
pipe.attach(kp.io.daq.TimesliceParser)
pipe.attach(k40.TwofoldCounter, tmax=10, dump_filename='../twofold_counts.p')
pipe.attach(Siphon, volume=10 * 60 * 180, flush=True)
pipe.attach(k40.K40BackgroundSubtractor)
pipe.attach(k40.IntraDOMCalibrator, ctmin=-1, det_id=DET_ID)
pipe.attach(
    IntraDOMCalibrationPlotter,
    det_oid="D0DU004MA",
    data_path='../data',
    plots_path='../plots')
pipe.attach(k40.ResetTwofoldCounts)
pipe.drain()
