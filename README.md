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
    

After that, use the following command to start the ``supervisor``:

    source setenv.sh
    make start

To see the status of the processes, use ``supervisorctl status``


You can stop and start individual services using ``supervisorctl stop
group:process_name`` and ``supervisorctl start group:process_name``

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
