SHELL := /bin/bash
SESSION_NAME := km3mon
DAQ_LIGIER := 192.168.0.110
STANDARD_TAGS := "IO_EVT, IO_SUM, IO_TSL, IO_TSL0, IO_TSL1, IO_TSL2, IO_TSSN, MSG, IO_MONIT"

default: start

start: 
	@echo Creating tmux session
	@tmux new-session -d -s ${SESSION_NAME} \
	    || (echo Please run \"make stop\" to close the current session.; exit 1)
	@tmux rename-window -t ${SESSION_NAME}:1 ligier

	@tmux send-keys -t ${SESSION_NAME}:ligier.1 \
	    "JLigier -d2 -P 5553" Enter
	@sleep 1  # wait a second for JLigier

	@tmux split-window -v -t ${SESSION_NAME}:ligier
	@tmux send-keys -t ${SESSION_NAME}:ligier.2 \
	    "ligiermirror -m \"${STANDARD_TAGS}\" ${DAQ_LIGIER}" Enter

stop:
	tmux kill-session -t ${SESSION_NAME}

.PHONY: start stop
