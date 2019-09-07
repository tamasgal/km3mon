# km3mon

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3268538.svg)](https://doi.org/10.5281/zenodo.3268538)

Online monitoring suite for the KM3NeT neutrino detectors.

## Requirements

 - Python 3.5+

Every other dependency will be installed or updated during the `make` procedure
via the Python package manager `pip`.

## Usage

First, install (or update) the requirements by typing

    make

Next, create a ``setenv.sh`` script according to the ``setenv_template.sh``
script and apply the detector settings. Here is an example configuration

```shell
#!/bin/bash
export DETECTOR_ID=43

# The ligier to get events (IO_EVT), timeslices (e.g. IO_TSSN) and
# summary slices (IO_SUM)
export DAQ_LIGIER_IP=192.168.0.110
export DAQ_LIGIER_PORT=5553
export TAGS_TO_MIRROR="IO_EVT, IO_SUM, IO_TSSN, MSG, IO_MONIT"

# The logger ligier (MSG)
export LOG_LIGIER_IP=192.168.0.119
export LOG_LIGIER_PORT=5553

# The command to start a ligier on the monitoring machine
# export LIGIER_CMD="JLigier"
export LIGIER_CMD="singularity exec /home/off1user/Software/Jpp_svn2git-rc9.sif JLigier"
export MONITORING_LIGIER_PORT=55530

export DETECTOR_MANAGER_IP=192.168.0.120

# The port for the KM3Web monitoring dashboard
export WEBSERVER_PORT=8081
# The port for the log viewer webserver
export LOGGING_PORT=8082

# The detector configuration to be used in the online reconstruction
export DETX="KM3NeT_00000043_03062019_t0set-A02087174.detx"
# Where to save the time residuals
export ROYFIT_TIMERES="data/time_residuals.csv"
```
    
Notice the `LIGIER_CMD` which in this case uses a Singularity image of Jpp.
The `DETX` needs to point to a recently calibrated DETX file otherwise the
live reconstruction will not work correctly.

For the weblog you need to download the latest version of `frontail`
https://github.com/mthenw/frontail/releases
and place it in e.g. `/usr/local/bin` (or another directory which is in
`$PATH`).

Before starting off, you also need to create a `supervisorctl.conf`. Usually
simply copying the `supervisorctl_template.conf` is enough, but make sure
to adjust some of the plots which monitoring only specific DUs.

After that, use the following command to start the ``supervisor``, which
you only need to do once:

    source setenv.sh
    make start

From now on ``supervisorctl`` is the tool to communicate with the monitoring
system. To see the status of the processes, use ``supervisorctl status``,
which will show each process one by one (make sure you call it in the
folder where you launched it):

```
$ supervisorctl status
ligiers:ligiermirror                  RUNNING   pid 611, uptime 1 day, 7:55:09
ligiers:monitoring_ligier             RUNNING   pid 610, uptime 1 day, 7:55:09
logging:msg_dumper                    RUNNING   pid 7466, uptime 1 day, 7:28:00
logging:weblog                        RUNNING   pid 7465, uptime 1 day, 7:28:00
monitoring_process:ahrs_calibration   RUNNING   pid 19612, uptime 1 day, 1:20:32
monitoring_process:dom_activity       RUNNING   pid 626, uptime 1 day, 7:55:09
monitoring_process:dom_rates          RUNNING   pid 631, uptime 1 day, 7:55:09
monitoring_process:pmt_hrv            RUNNING   pid 633, uptime 1 day, 7:55:09
monitoring_process:pmt_rates          RUNNING   pid 632, uptime 1 day, 7:55:09
monitoring_process:rttc               RUNNING   pid 9717, uptime 10:55:53
monitoring_process:trigger_rates      RUNNING   pid 637, uptime 1 day, 7:55:09
monitoring_process:triggermap         RUNNING   pid 638, uptime 1 day, 7:55:09
monitoring_process:ztplot             RUNNING   pid 7802, uptime 1 day, 7:26:13
webserver                             RUNNING   pid 29494, uptime 1 day, 0:34:23
```

The processes are grouped accordingly (ligier, monitoring_process etc.) and
automaticallly started in the right order.

You can stop and start individual services using ``supervisorctl stop
group:process_name`` and ``supervisorctl start group:process_name``

Since the system knows the order, you can safely ``restart all`` or just
a group of processes. Use the ``supervisorctl help`` to find out more and
``supervisorctl help COMMAND`` to get a detailed description of the
corresponding command.

To shut down the monitoring service completely, use ``make stop``.


## Configuration file

A file called `pipeline.toml` can be placed into the root folder of the
monitoring software (usually `~/monitoring`) which can be used to set
different kind of parameters, like plot attributes or ranges.
Here is an example `pipeline.toml`:

```
[WebServer]
username = "km3net"
password = "swordfish"

[DOMRates]
lowest_rate = 150  # [kHz]
highest_rate = 350  # [kHz]

[PMTRates]
lowest_rate = 1000  # [Hz]
highest_rate = 20000  # [Hz]

[TriggerRate]
interval = 300  # time inverval to integrate [s]
with_minor_ticks = true  # minor tickmarks on the plot

[TriggerMap]
max_events = 5000  # the number of events to log

[ZTPlot]
min_dus = 1
ytick_distance = 25  # [m]
```
