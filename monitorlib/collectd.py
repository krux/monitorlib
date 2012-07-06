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

 likewise, you can use it to output values:
 collectd.metric("path/to/metric", value)

 ==
 The following options require using bin/collectd_notify as the notification plugin:

 If the optional 2nd argument ("page") is True, pagerduty will be triggered.

 A 3rd, optional argument, can be an email address to notify, or list of emails.

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

def notify_output(severity, message, page, email):
    ''' formats and returns a collectd notification (str) '''
    timestamp = int(time.mktime(time.gmtime()))
    message = "%s %s: %s" % (FQDN.split('.')[0], CALLER, message)

    if page:
        message = 'PD' + message
    if email:
        message = str(email) + 'ENDEMAIL' + message

    return "PUTNOTIF severity=%s time=%i host=%s message=%s" % (severity, timestamp, FQDN, message)

def failure(string, page=False, email=False):
    return notify_output('failure', string, page, email)

def warning(string, page=False, email=False):
    return notify_output('warning', string, page, email)

def ok(string, page=False, email=False):
    return notify_output('okay', string, page, email)

def metric(path, value):
    ''' formats and returns a collectd metric value (str) '''
    return "PUTVAL %s/%s interval=%s N:%s" % (FQDN, path, INTERVAL, value)


