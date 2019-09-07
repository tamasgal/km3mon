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
export LIGIER_CMD="JLigier"
export MONITORING_LIGIER_PORT=55530

export DETECTOR_MANAGER_IP=192.168.0.120

# The port for the KM3Web monitoring dashboard
export WEBSERVER_PORT=8081
# The port for the log viewer webserver
export LOGGING_PORT=8082

# The detector configuration to be used in the online reconstruction
export DETX=""
# Where to save the time residuals
export ROYFIT_TIMERES="data/time_residuals.csv"
