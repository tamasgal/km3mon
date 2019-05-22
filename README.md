# km3mon

Monitoring facility for the KM3NeT neutrino detector.

## Requirements

 - Python 3.5+

Every other dependency will be installed or updated during the `make` procedure
via the Python package manager `pip`.

## Usage

First, install (or update) the requirements by typing

    make

Next, modify the ``setenv.sh`` script according to the detector setup.
Here is an example configuration

```shell
#!/bin/bash
export DETECTOR_ID=43
export DAQ_LIGIER_IP=192.168.0.110
export DAQ_LIGIER_PORT=5553
export DETECTOR_MANAGER_IP=192.168.0.120
export MONITORING_LIGIER_PORT=55530
export WEBSERVER_PORT=8081
export LOGGING_PORT=8082
export LIGIER_CMD="JLigier"
export TAGS_TO_MIRROR="IO_EVT, IO_SUM, IO_TSL, IO_TSL0, IO_TSL1, IO_TSL2, IO_TSSN, MSG, IO_MONIT"
```
    

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


## Configuration file

A file called `pipeline.toml` can be placed into the root folder of the
monitoring software (usually `~/monitoring`) which can be used to set
different kind of parameters, like plot attributes or ranges.
Here is an example `pipeline.toml`:

```
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
