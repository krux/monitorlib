monitorlib
==========

Python library for creating monitoring scripts/plugins.

Install via:
    pip install -e "git+https://github.com/krux/monitorlib.git#egg=monitorlib"

cloudkick
---------
A cloudkick library to assist with text formatting, to output cloudkick compatible
metrics and status messages.

collectd
--------
Library for writing collectd Exec plugins in python. Very simple interface to
output metrics or status messages: ok("message"), failure("message"), etc.
See examples/ and collectd.py for documentation.

This library does not use the collectd PUTNOTIF-style alerting mechanism. It's
too limiting. Instead, you can set defaults by wrapping the library, and for 
example, have warning messages only email, and failure/ok messages page.

Also includes pagerduty integration, with support for storing the incident_key
returned by pagerduty in redis (or flat files), to avoid duplicate alerts.

