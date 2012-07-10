#
# Author: Charlie Schluting <charlie@krux.com>
#
"""
 Library to make outputting notifications and values in collectd plugins easier.
 Handles notifications itself; supports email, pagerduty, arbitrary URL to POST
 JSON to.

 = Usage:
 See: examples/collectd_check.py

 Within your own collectd plugin, simply:
 import monitorlib.collectd as collectd

 Then, you can use collectd.[warning|ok|failure]("message content"),
 and the lib will output a notification in the correct
 format (timestamp, hostname, etc).

 likewise, you can use it to output values:
 collectd.metric("path/to/counter", value)


 = Interface docs:

  == ok("status message", [page=True], [email='A@host,B@host'], [url])
  == warning("status message", [page=True], [email='A@host,B@host'], [url])
  == failure("status message", [page=True], [email='A@host,B@host'], [url])

  Arguments:
  message: text of the alert
  page: set to true to initiate sending to pagerduty. Must have collectdlib_config.py
        configured with PD_KEY (service_key from pagerduty)
  email: one or more comma-separated emails to send to: 'user@host,user2@host'
  url: URL to HTTP POST the JSON alert to

  == optional configuration (required to enable some options):
    === set_pagerduty_key("12309423enfjsdjfosiejfoiw") to set pagerduty auth
    === set_pagerduty_store([file|redis], [path])
        Location to store state information on outstanding alerts.
        To use redis: call set_redis_config() (see below)
        Default is: set_pagerduty_store('file', '/tmp/incident_keys')
    === set_redis_config(writer_host, reader_host, port, password, [db]) to enable checking
        with redis for disabled alerts

  == metric("testing/records", int)

  Arguments:
  metric: string of collectd metric (excluding host, it's added automatically) -
          make sure it's formatted as collectd expects, or it'll be dropped!
          (make sure last item is in /usr/share/collectd/types.db, to start)
          Krux-specific: always append /counter, and it'll be removed by graphite.
          To get stats.$env.ops.collectd.$host.my_metric, use "my_metric/counter".
  value: integer value

"""
import time
import socket
import os
import sys
import inspect
import logging
import urllib2
import smtplib
from optparse import OptionParser
import monitorlib.pagerduty as pagerduty
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
try:
    import simplejson as json
except ImportError:
    import json

try:
    import redis
except ImportError:
    pass

FQDN = os.environ.get('COLLECTD_HOSTNAME', socket.getfqdn())
INTERVAL = os.environ.get('COLLECTD_INTERVAL', "60")
#CALLER = os.path.basename(inspect.stack()[-1][1])
CALLER = os.path.basename(sys.argv[0])
TIME = int(time.mktime(time.gmtime()))
DATASTORE = None

def set_datastore(store):
    global DATASTORE
    DATASTORE = store

def set_pagerduty_key(key):
    global PD_KEY
    PD_KEY = key

def set_redis_config(writer_host, reader_host, port, password, db='db0'):
    global REDIS_CONFIG
    REDIS_CONFIG = { 'writer': writer_host,
                     'reader': reader_host,
                     'port': port,
                     'passwd': password,
                     'db': db,
                   }
    set_datastore('redis')

def send_to_socket(message, host, port):
    """
    Sends message to host/port via tcp
    """
    sock = socket.socket()

    sock.connect((host, int(port)))
    sock.sendall(message)
    sock.close()

def post_to_url(message, url):
    """
    HTTP POSTs message to url
    """
    req = urllib2.Request(url, json.dumps(message), {'Content-Type': 'application/json'})
    f = urllib2.urlopen(req)
    resp = f.read()
    f.close()

    return resp

def set_pagerduty_store(kind='file', config='/tmp/incident_keys'):
    global PD_STORAGE_CONFIGURED
    if pagerduty.set_datastore(kind, config):
        PD_STORAGE_CONFIGURED = True

def send_to_pagerduty(key, message):
    """
    Sends alert to pager duty - you must call authenticate() first
    """
    # if not already done, call config function to set defaults
    if 'PD_STORAGE_CONFIGURED' not in globals():
        if 'REDIS_CONFIG' in globals():
            set_pagerduty_store('redis', REDIS_CONFIG)
        else:
            set_pagerduty_store()

    pagerduty.authenticate(key)

    send_string = "%s %s: %s %s" % (message['host'], message['plugin'], message['severity'].upper(), message['message'])

    if 'okay' in message['severity']:
        pagerduty.event('resolve', send_string)

    elif 'failure' or 'warning' in message['serverity']:
        pagerduty.event('trigger', send_string)

def send_to_email(address, message):
    """
    Sends alert via email
    """
    print "emailing: ", address

    alert_subject = "%s %s: %s %s" % (message['host'], message['plugin'], message['severity'].upper(), message['message'])

    me = 'collectd@krux.com'
    you = str(address)

    msg = MIMEMultipart()
    msg['Subject'] = '[collectd] %s %s' % (message['severity'], alert_subject)
    msg['From'] = me
    msg['To'] = you
    body = MIMEText(str(message))
    msg.attach(body)

    s = smtplib.SMTP('localhost')
    s.sendmail(me, [you], msg.as_string())
    s.quit()

def check_redis_alerts_disabled(message):
    """
    Check redis to see if alerts are disabled for this host - times out after 2 seconds,
    to not block on an unreachable redis server.
    """
    conf = REDIS_CONFIG

    # key: host value: list of plugins that are disabled
    conn = redis.Redis(conf['reader'], conf['port'], conf['db'], conf['passwd'], socket_timeout=2)
    result = conn.get(message['host'])

    if '*' in result or message['plugin'] in result:
        return True
    else:
        return False

def dispatch_alert(severity, message, page, email, url):
    ''' dispatch_alertes alerts based on params '''

    message = json.loads('{"host": "%s", "plugin": "%s", "severity": "%s", "message": "%s"}' % (FQDN.split('.')[0], CALLER, severity, message))

    # check if notifications for this host are disabled, and exit if so
    if DATASTORE and 'redis' in DATASTORE:
        if 'REDIS_CONFIG' not in globals():
            logging.error("must call redis_config(), first")
        elif check_redis_alerts_disabled(message):
            logging.info("alerting disabled, supressing alert for: %s, %s" % (message['host'], message['plugin']))
        #    sys.exit(0)

    # if paging was requested, do it
    if page:
        if 'PD_KEY' not in globals():
            logging.error("must call set_pagerduty_key(), first")
        else:
            send_to_pagerduty(PD_KEY, message)

    if email:
        send_to_email(email, message)
    if url:
        post_to_url(message, url)



def failure(string, page=False, email=False, url=False):
    return dispatch_alert('failure', string, page, email, url)

def warning(string, page=False, email=False, url=False):
    return dispatch_alert('warning', string, page, email, url)

def ok(string, page=False, email=False, url=False):
    return dispatch_alert('okay', string, page, email, url)

def metric(path, value):
    ''' formats and returns a collectd metric value (str) '''
    return "PUTVAL %s/%s interval=%s N:%s" % (FQDN, path, INTERVAL, value)


