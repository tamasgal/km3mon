# km3mon

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3268538.svg)](https://doi.org/10.5281/zenodo.3268538)

Online monitoring suite for the KM3NeT neutrino detectors.

## Requirements

 - Docker and Docker Compose

Everything is containerised, so no need to install other software.

## Setup

1. Create a file called `.env` from the `example.env` template and adjust the detector
   ID and the IP/port of the servers.

2. Next, create a `backend/supervisord.conf` from the template file
   `backend/supervisord.conf.example` and adjust if needed.

3. Create a `backend/pipeline.toml` from the `backend/pipeline.toml.example`
   and adapt the settings if needed. Don't forget to add operators and shifters.

4. Optionally, adapt the layout of the plots in `frontend/routes.py`.

## Start and stop

The monitoring system can be started using

    docker-compose up -d

This will download and build all the required images and launch the containers
for each service. It will also create an overlay network.

To stop it it

    docker-compose down

## Monitoring the monitoring

Log files are kept in `logs/`, data dumps in `data/` and plots in `plots/`.

To check the logs or follow them in real-time (`-f`) and limit the rewind
to a number of lines `--tail=N`, e.g.

    docker-compose logs -f --tail=10 SERVICE_NAME

The `SERVICE_NAME` can be any of `backend`, `frontend`, `ligier`, `ligiermirror`,
`ligierlogmirror`, `reco` or `livelog`.

The monitoring back-end is running inside a Docker container and controlled
by `supervisord`. You can enter the `backend` with

    docker exec -it monitoring_backend_1 bash

The ``supervisorctl`` is the tool to communicate with the monitoring
back-end system. To see the status of the processes, use `supervisorctl status`,
it will show each process one by one (make sure you call it in the
folder where you launched it):

```
$ supervisorctl status
alerts:timesync_monitor               RUNNING   pid 26, uptime 1 day, 5:21:06
logging:chatbot                       RUNNING   pid 11, uptime 1 day, 5:21:06
logging:log_analyser                  RUNNING   pid 10, uptime 1 day, 5:21:06
logging:msg_dumper                    RUNNING   pid 9, uptime 1 day, 5:21:06
monitoring_process:acoustics          RUNNING   pid 1567, uptime 1 day, 5:20:59
monitoring_process:ahrs_calibration   RUNNING   pid 91859, uptime 1:09:14
monitoring_process:dom_activity       RUNNING   pid 1375, uptime 1 day, 5:21:00
monitoring_process:dom_rates          RUNNING   pid 1378, uptime 1 day, 5:21:00
monitoring_process:pmt_rates_10       RUNNING   pid 1376, uptime 1 day, 5:21:00
monitoring_process:pmt_rates_11       RUNNING   pid 1379, uptime 1 day, 5:21:00
monitoring_process:pmt_rates_13       RUNNING   pid 1377, uptime 1 day, 5:21:00
monitoring_process:pmt_rates_14       RUNNING   pid 1568, uptime 1 day, 5:20:59
monitoring_process:pmt_rates_18       RUNNING   pid 21, uptime 1 day, 5:21:06
monitoring_process:pmt_rates_9        RUNNING   pid 1566, uptime 1 day, 5:20:59
monitoring_process:rttc               RUNNING   pid 118444, uptime 0:17:20
monitoring_process:trigger_rates      RUNNING   pid 22, uptime 1 day, 5:21:06
monitoring_process:triggermap         RUNNING   pid 1796, uptime 1 day, 5:20:58
monitoring_process:ztplot             RUNNING   pid 24, uptime 1 day, 5:21:06
reconstruction:time_residuals         RUNNING   pid 27, uptime 1 day, 5:21:06
```

The processes are grouped accordingly (logging, monitoring_process etc.) and
automatically started in the right order.

You can stop and start individual services using ``supervisorctl stop
group:process_name`` and ``supervisorctl start group:process_name``

Since the system knows the order, you can safely ``restart all`` or just
a group of processes. Use the ``supervisorctl help`` to find out more and
``supervisorctl help COMMAND`` to get a detailed description of the
corresponding command.

## Back-end configuration file

The file `backend/pipeline.toml` is the heart of all monitoring processes and
can be used to set different kind of parameters, like plot attributes or ranges.

## Chatbot

The `km3mon` suite comes with a chatbot which can join a channel defined
in the `pipeline.toml` file under the `[Alerts]` section:

``` toml
[Alerts]
botname = "monitoring"
password = "supersecretpassword"
channel = "operations_fr"
operators = [ "a_enzenhoefer", "tamasgal",]
```

The password is the actual login password of the bot. Once the `chatbot` service
is running, the bot will notifiy important events like sudden drop of the
trigger rate and can also be used to retrieve information from the monitoring
system, set the current shifts and even control the monitoring services through
the `supervisorctl` interface. Only the operators defined in the configuration
file are allowed to modify services or change the shifters.
To see the bot's capabilities, one simply asks them for help via
`@monitoring help`:

```
Hi Tamas Gal, I was built to take care of the monitoring alerts.
Here is how you can use me:
- @monitoring shifters are cnorris and bspencer
-> set the new shifters who I may annoy with chat messages and
emails.
- @monitoring status -> show the status of the monitoring system
- @monitoring supervisorctl -> take control over the monitoring system
- @monitoring help -> show this message
```
