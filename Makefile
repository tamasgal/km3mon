SHELL := /bin/bash

default: build

build:
	pip install -Ur requirements.txt

start: 
	@echo Starting supervisord
	supervisord -c supervisord.conf

.PHONY: build start stop
