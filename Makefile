SHELL := /bin/bash

default: build

build:
	pip install -Ur requirements.txt

start: 
	@echo Starting supervisord
	supervisord -c supervisord.conf

stop: 
	@echo Shutting down supervisord
	supervisorctl shutdown

.PHONY: build start stop
