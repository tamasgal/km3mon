# km3mon

Monitoring facility for the KM3NeT neutrino detector.

## Usage

First, install the requirements by typing

    make

The `make` command can also be used to update the requirements.

Next check out the `configure` options with

    ./configure --help

and configure the ``Makefile`` with

    ./configure --your --options

Finally everything is set up. To start the monitoring facility, type

    make start

If you want to stop it:

    make stop

easy.
