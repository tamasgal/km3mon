Unreleased changes
------------------

Version 1
---------

2.0.0 / 2021-05-05
~~~~~~~~~~~~~~~~~~

* Fully dockerised monitoring system
* Log analyser added by Rodri <rgracia@km3net.de>
* Log files are now showing plots indicating the number of errors and warnings
  thanks to Rodri <rgracia@km3net.de>
* Corrupt event data are now skipped in trigger rate, which previously crashed
  the thread
* Several catches of errors in online processing to make things run and log
  instead of crash and annoy
* Preliminary support for km3pipe v9


1.2.0 / 2019-11-25
~~~~~~~~~~~~~~~~~~

* Top 10 events are now saved
* Added automatic ELOG entry for massive evenets, monitored in ``ztplot.py``

1.1.1 / 2019-10-23
~~~~~~~~~~~~~~~~~~

* Several bugfixes and improvements


1.1.0 / 2019-10-03
~~~~~~~~~~~~~~~~~~

* Several bugfixes and improvements


1.0.0 / 2019-06-29
~~~~~~~~~~~~~~~~~~

* First major release, using supervisord
