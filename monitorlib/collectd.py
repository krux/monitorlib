#!/usr/bin/env kpython
#
# Author: Charlie Schluting <charlie@krux.com>
#
# Library to make outputting notifications and values in collectd plugins easier.
#
# usage:
# Within your own collectd plugin, simply:
# import collectd
#
# Then, you can use collectd.failure("message content"),
# and the lib will output a notification in the correct format (timestamp, hostname, etc).
#
# likewise, you can use it to output values:
# collectd.metric("path/to/metric", value)
#
import time
import socket
import os
import sys

if 'COLLECTD_HOSTNAME' in os.environ: fqdn = os.environ['COLLECTD_HOSTNAME']
else: fqdn = socket.getfqdn()

if 'COLLECTD_INTERVAL' in os.environ: interval = os.environ['COLLECTD_INTERVAL']
else: interval = "60"

def notify_output(severity, message):
    ''' formats and prints out a collectd notification '''
    timestamp = int(time.mktime(time.gmtime()))
    output = "PUTNOTIF severity=%s time=%i host=%s message=%s" % (severity, timestamp, fqdn, message)
    print output

def failure(string):
    notify_output('failure', string)

def warning(string):
    notify_output('warning', string)

def ok(string):
    notify_output('okay', string)

def metric(path, value):
    output = "PUTVAL %s/%s interval=%s N:%s" % (fqdn, path, interval, value)
    print output


