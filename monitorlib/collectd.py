#
# Author: Charlie Schluting <charlie@krux.com>
#
"""
 Library to make outputting notifications and values in collectd plugins easier.

 usage:
 Within your own collectd plugin, simply:
 import collectd

 Then, you can use collectd.failure("message content"),
 and the lib will output a notification in the correct format (timestamp, hostname, etc).

 likewise, you can use it to output values:
 collectd.metric("path/to/metric", value)
"""

import time
import socket
import os
import sys

FQDN = os.environ.get('COLLECTD_HOSTNAME', socket.getfqdn())
INTERVAL = os.environ.get('COLLECTD_INTERVAL', "60")


def notify_output(severity, message):
    ''' formats and returns a collectd notification (str) '''
    timestamp = int(time.mktime(time.gmtime()))
    #TODO: insert name of calling script in message
    return "PUTNOTIF severity=%s time=%i host=%s message=%s" % (severity, timestamp, FQDN, message)

def failure(string):
    return notify_output('failure', string)

def warning(string):
    return notify_output('warning', string)

def ok(string):
    return notify_output('okay', string)

def metric(path, value):
    ''' formats and returns a collectd metric value (str) '''
    return "PUTVAL %s/%s interval=%s N:%s" % (FQDN, path, INTERVAL, value)


