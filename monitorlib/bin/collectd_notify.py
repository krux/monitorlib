#!/usr/bin/env python
#
# Author: Charlie Schluting <charlie@krux.com>
#

"""
  Collectd notification plugin (reads notifications generated by collectd plugins):
  converts to JSON, and forwards messages via HTTP POST, or directly to a raw tcp port.

  Also, supports sending to pagerduty if the message has the text 'PD', and pd-key command
  line option was used.

input format:

Severity: FAILURE
Time: 1200928930
Host: myhost.mydomain.org
\n
This is a message...

"""
import time
import socket
import os
import sys
import logging
import urllib
import urllib2
from optparse import OptionParser
import monitorlib.pagerduty as pagerduty

try:
    import simplejson as json
except ImportError:
    import json

def convert_to_json(message):
    """
    converts input (as formatted by collectd) to json
    """

    output = dict([line.split(': ', 1) for line in message.split('\n')[:3]])
    try:
        output.update({'Message': ''.join(message.split('\n')[3:])})
    except IndexError:
        output.update('Message', '')

    return json.dumps(output)

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

def send_to_pagerduty(key, message):
    """
    Sends alert to pager duty - you must call authenticate() first
    """
    authenticate(key)

    if 'OKAY' in message['Severity']:
        pagerduty.event('resolve', message['Message'])

    elif 'FAILURE' or 'WARNING' in message['Serverity']:
        pagerduty.event('trigger', message['Message'])

if __name__ == '__main__':

    parser = OptionParser("usage: %prog [options]")
    parser.add_option("-d", "--debug", default=None, action="store_true", help="enable debug output")
    parser.add_option("--http-server", help="HTTP server to post message to (url)")
    parser.add_option("--server", help="server to post message to (host:port) via TCP")
    parser.add_option("--pd-key", help="your pagerduty service_key, enables paging")
    (options, args) = parser.parse_args()

    # set up logging
    if options.debug: log_level = logging.DEBUG
    else:             log_level = logging.INFO

    logging.basicConfig(stream=sys.stdout, level=log_level)
    logging.basicConfig(stream=sys.stderr, level=(logging.ERROR,logging.CRITICAL))

    stdin = sys.stdin.read()
    if not stdin:
        logging.error("did not receive any message on stdin, exiting..")
        sys.exit(1)

    message = convert_to_json(stdin)

    if options.server:
        host, port = options.server.split(":")
        send_to_socket(message, host, port)
    elif options.http_server:
        post_to_url(message, options.http_server)
    else:
        print message

    if options.pd_key and 'PD' in message['Message']:
        send_to_pagerduty(options.pd_key, message.lstrip('PD'))


