# km3mon

Monitoring facility for the KM3NeT neutrino detector.

## Requirements

There are two requirements needed:

 - Python 3.5+
 - tmux

Both of them should be available ony any DAQ system you encounter. If not,
contact the administrators.

Every other dependency will be installed or updated during the `make` procedure
via the Python package manager `pip`.

## Usage

First, install (or update) the requirements by typing

    make

Next check out the `configure` options with

    ./configure --help
    
which will print the following screen:

```
 _  _  __  __  ___  __  __  _____  _  _
( )/ )(  \/  )(__ )(  \/  )(  _  )( \( )
 )  (  )    (  (_ \ )    (  )(_)(  )  (
(_)\_)(_/\/\_)(___/(_/\/\_)(_____)(_)\_)

Usage:  ./configure [options]

  OPTION                    DESCRIPTION                    DEFAULT
  --detector-id             Detector ID                    29
  --daq-ligier-ip           DAQ Ligier                     192.168.0.110
  --daq-ligier-port         Port of the DAQ Ligier         5553
  --monitoring-ligier-port  Port of the monitoring Ligier  5553
  --tmux-session-name       TMUX session name              km3mon
  --webserver-port          Port of the web server         8080

All invalid options are silently ignored.
```

and configure the ``Makefile`` with

    ./configure --your --options

After that, a `Makefile` is generated and you can start the monitoring facility
with

    make start

If you want to stop it:

    make stop

easy.
