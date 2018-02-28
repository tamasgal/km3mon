SHELL := /bin/bash
SESSION_NAME := km3mon

default: start

start: 
	@echo Creating tmux session
	@tmux new-session -d -s ${SESSION_NAME} \
	    || (echo Please run \"make stop\" to close the current session.; exit 1)
	@tmux rename-window -t ${SESSION_NAME}:1 ligier
	@tmux send-keys -t km3mon:ligier.1 "JLigier -d2 -P 5553" Enter

stop:
	tmux kill-session -t ${SESSION_NAME}

.PHONY: start stop
