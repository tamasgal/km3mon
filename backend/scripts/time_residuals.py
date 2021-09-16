#!/usr/bin/env python
# coding=utf-8
# vim: ts=4 sw=4 et
"""
Creates time residuals plots.

Usage:
    time_residuals.py [options] TIME_RESIDUALS_FILE
    time_residuals.py (-h | --help)

Options:
    -o PLOT_DIR     The directory to save the plot [default: /plots].
    -h --help       Show this screen.

"""
import os
from datetime import datetime
import time
import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import km3pipe as kp
kp.style.use('km3pipe')


def main():
    from docopt import docopt
    args = docopt(__doc__)

    plots_path = args['-o']
    hours = 2

    while True:
        print("Reading data...")
        df = pd.read_csv(args['TIME_RESIDUALS_FILE'])
        df = df[df.timestamp > time.time() - 60 * 60 * hours]
        print(f" -> number of entries: {len(df)}")

        fig, axes = plt.subplots(nrows=6,
                                 ncols=3,
                                 figsize=(16, 22),
                                 sharex=True,
                                 sharey=False,
                                 constrained_layout=True)

        for ax, floor in zip(axes.flatten(), range(1, 19)):
            for du in np.unique(df.du):
                _df = df[df.du == du]
                t_res = _df[_df.floor == floor].t_res
                t_res = t_res[np.abs(t_res) < 500]
                print(f"   DU {du} floor {floor}: {len(t_res)} entries")
                ax.hist(t_res,
                        bins=100,
                        histtype='step',
                        lw=2,
                        label=f'Floor {floor} / DU {du}')
            ax.legend(loc='upper right')
            if floor > 15:
                ax.set_xlabel('time residual [ns]')
            if floor % 3 == 1:
                ax.set_ylabel('count')
            ax.set_yscale('log')
        utc_now = datetime.utcnow().strftime("%c")
        fig.suptitle(f"Time residuals using ROy reconstructions "
                     f"from the past {hours} hours - "
                     f"{utc_now} UTC\n")
        plt.savefig(os.path.join(plots_path, 'time_residuals'))
        plt.close('all')

        time.sleep(60)


if __name__ == '__main__':
    main()
