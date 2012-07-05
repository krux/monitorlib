#
# Author: Charlie Schluting <charlie@krux.com>
#
"""
 Library to make outputting notifications and values in collectd plugins easier.

 usage:
 Within your own collectd plugin, simply:
 import monitorlib.collectd as collectd

 Then, you can use collectd.failure("message content"),
 and the lib will output a notification in the correct format (timestamp, hostname, etc).
 If the optional 2nd argument ("pageme") is True, pagerduty will be triggered.

 likewise, you can use it to output values:
 collectd.metric("path/to/metric", value)
"""

import time
import socket
import os
import sys
import inspect

FQDN = os.environ.get('COLLECTD_HOSTNAME', socket.getfqdn())
INTERVAL = os.environ.get('COLLECTD_INTERVAL', "60")
#CALLER = os.path.basename(inspect.stack()[-1][1])
CALLER = os.path.basename(sys.argv[0])

def notify_output(severity, message, pageme=False):
    ''' formats and returns a collectd notification (str) '''
    timestamp = int(time.mktime(time.gmtime()))
    message = "%s: %s" % (CALLER, message)
    if pageme: message = 'PD' + message

    return "PUTNOTIF severity=%s time=%i host=%s message=%s" % (severity, timestamp, FQDN, message)

def failure(string, pageme=False):
    return notify_output('failure', string, pageme)

def warning(string, pageme=False):
    return notify_output('warning', string, pageme)

def ok(string, pageme=False):
    return notify_output('okay', string, pageme)

def metric(path, value):
    ''' formats and returns a collectd metric value (str) '''
    return "PUTVAL %s/%s interval=%s N:%s" % (FQDN, path, INTERVAL, value)


