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
	ps aux|grep gunicorn|awk '{print $2}'|xargs kill -9

.PHONY: build start stop
