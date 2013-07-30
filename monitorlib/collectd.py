#
# Author: Charlie Schluting <charlie@krux.com>
#
"""
 Library to make outputting notifications and values in collectd plugins easier.
 Handles notifications itself; supports email, pagerduty, arbitrary URL to POST
 JSON to (or even raw TCP sending of JSON), and sending events to riemann.

 = Usage:
 See: examples/collectd_check.py

 Within your own collectd plugin, simply:
 import monitorlib.collectd as collectd

 Create an object:
 cd = collectd.Client()

 Then, you can use cd.[warning|ok|failure]("message content", [options]).

 likewise, you can use it to output values:
 cd.metric("plugin-instance/type-instance", value)

 = Interface docs:

  == ok("status message", [page=True], [email='A@host,B@host'], [url], [riemann])
  == warning("status message", [page=False], [email='A@host,B@host'], [url], [riemann])
  == failure("status message", [page=True], [email='A@host,B@host'], [url], [riemann])

  Arguments:
  message: text of the alert
  page: set to true to initiate sending to pagerduty. Must have called
        set_pagerduty_key() first.
  email: one or more comma-separated emails to send to: 'user@host,user2@host'
  url: URL to HTTP POST the JSON alert to
  riemann: send event to riemann. must call configure_riemann() first.

  == optional configuration (required to enable some options):
    === set_pagerduty_key("12309423enfjsdjfosiejfoiw") to set pagerduty auth
    === set_pagerduty_store([file|redis], [path])
        Location to store state information on outstanding alerts.
        To use redis: call set_redis_config() (see below)
        Default is: set_pagerduty_store('file', '/tmp/incident_keys')
    === set_redis_config(writer_host, reader_host, writer_port, reader_port, password, [db])
        to enable checking with redis for disabled alerts, and pagerduty incident_keys.
    === configure_riemann(host, port) of the riemann server

  == metric("testing/records", int)

  Arguments:
  metric: string of collectd metric (excluding host, it's added automatically) -
          make sure it's formatted as collectd expects, or it'll be dropped!
          (make sure last item is in /usr/share/collectd/types.db, to start)
          Krux-specific: always use the gauge type, and it'll be removed by graphite. Counters are derived.
          To get stats.$env.ops.collectd.$host.plugin.instance.foo, use "plugin-instance/gauge-foo".
  value: integer value

 = Thoughts:
  You can use this to send to pagerduty or elsewhere directly through your service
  check plugins. But, that's old-school nagios style.
  Ideally, you'll simply wrap this library to set the defaults to False for everything
  but riemann. This will send all events to riemann.
  In riemann, you can verify the state of other checks (LB status, cluster health, parent relationships,
  etc) before alerting (or even displaying a status) for real.

"""
import socket
import os
import sys
import subprocess
import inspect
import logging
import urllib2
import smtplib
import time
from time import gmtime, strftime
from optparse import OptionParser
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
try:
    import simplejson as json
except ImportError:
    import json

# if these imports fail, using those components won't work, but they aren't required deps:
try:
    import redis
except ImportError:
    pass

try:
    import bernhard
except ImportError:
    pass

import monitorlib.pagerduty as pagerduty

class Client:

    def __init__(self, page=False, email=False, url=False, riemann=False, disable_alerts=False):
        self.page = page
        self.email = email
        self.url = url
        self.riemann = riemann
        self.riemann_tags = []
        self.redis_config = None
        self.datastore = 'file'
        self.pagerduty_configured = None
        self.pagerduty_key = None
        self.fqdn = os.environ.get('COLLECTD_HOSTNAME', socket.gethostname())
        self.interval = os.environ.get('COLLECTD_INTERVAL', "60")
        # CALLER = os.path.basename(inspect.stack()[-1][1])
        self.caller = os.path.basename(sys.argv[0])
        self.time = int(time.mktime(time.gmtime()))
        self.state_dir = '/tmp'
        self.state_file = self.state_dir + "/%s" % self.caller
        self.cur_state = None
        self.alert_message = None
        self.alert_on_status_string_changes = True
        self.no_alerts = disable_alerts

    def failure(self, string, page=None, email=None, url=None, riemann=None):
        if page is None:
            page = self.page
        if email is None:
            email = self.email
        if url is None:
            url = self.url

        # we store data (the conf) in self.riemann. If it's not passed as an arg, use self.riemann.
        if riemann is None or riemann is True:
            riemann = self.riemann

        self.dispatch_alert('failure', string, page, email, url, riemann)

    def warning(self, string, page=None, email=None, url=None, riemann=None):
        if page is None:
            page = self.page
        if email is None:
            email = self.email
        if url is None:
            url = self.url

        # we store data (the conf) in self.riemann. If it's not passed as an arg, use self.riemann.
        if riemann is None or riemann is True:
            riemann = self.riemann

        self.dispatch_alert('warning', string, page, email, url, riemann)

    def ok(self, string, page=None, email=None, url=None, riemann=None):
        if page is None:
            page = self.page
        if email is None:
            email = self.email
        if url is None:
            url = self.url

        # we store data (the conf) in self.riemann. If it's not passed as an arg, use self.riemann.
        if riemann is None or riemann is True:
            riemann = self.riemann

        self.dispatch_alert('okay', string, page, email, url, riemann)

    def metric(self, path, value):
        ''' formats and returns a collectd metric value (str) '''
        return "PUTVAL %s/%s interval=%s N:%s" % (self.fqdn, path, self.interval, value)

    def cmd(self, command):
        """ Helper for running shell commands with subprocess().
            Returns: (stdout, stderr)
        """
        process = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        return process.communicate()

    def set_alert_on_status_string_changes(self, toggle=True):
        """
        dis/en -ables alerting on status string changes (only the state will trigger alerts)
        """
        self.alert_on_status_string_changes = toggle

    def set_pagerduty_store(self, kind='file', config='/tmp/incident_keys'):
        """
        sets PD storage method, and stores a variable to indicate this has been done
        """
        if pagerduty.set_datastore(kind, config):
            self.pagerduty_configured = True

    def configure_riemann(self, host, port):
        """
        configures host, port for sending events to riemann.
        """
        self.riemann = {'host': host, 'port': port, }

    def set_redis_config(self, writer_host, reader_host, writer_port, reader_port, password, db='db0'):
        self.redis_config = {'writer': writer_host,
                             'reader': reader_host,
                             'writer_port': writer_port,
                             'reader_port': reader_port,
                             'passwd': password,
                             'db': db,
                             }
        self.datastore = 'redis'

    def set_state_dir(self, dir):
        self.state_dir = dir
        self.state_file = dir + "/%s" % self.caller

    def disable_alerts():
        self.no_alerts = True

    def check_redis_alerts_disabled(self, message):
        """
        Check redis to see if alerts are disabled for this host - times out after 2 seconds,
        to not block on an unreachable redis server.
        """
        conf = self.redis_config

        # key: host, value: list of plugins that are disabled (or '*' for all)
        conn = redis.Redis(conf['reader'], conf['reader_port'], conf['db'], conf['passwd'], socket_timeout=2)

        if not conn:
            return False
        else:
            global_acks = conn.get('global')
            if global_acks and ('*' in global_acks or message['plugin'] in global_acks):
                return True
            else:
                result = conn.get(message['host'])

        if result and ('*' in result or message['plugin'] in result):
            return True
        else:
            return False

    def get_current_state(self):
        """
        Returns "new" if it can't open the state_file. Otherwise, returns the text in the file.
        """

        if not os.path.exists(self.state_file):
            return "new"

        with open(self.state_file, 'r') as fh:
            return fh.readline()

    def dispatch_alert(self, severity, message, page, email, url, riemann):
        """
        dispatch_alerts alerts based on params, and keep state, etc...
        """

        now = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        message = {"host": self.fqdn.split('.')[0], "plugin": self.caller, "severity": severity, "message": message}

        # print the error, so when running plugins by hand we see the current state
        # (collectd will ignore ill-formatted messages)
        print "Dispatching alert with severity %s: %s." % (severity, message)

        # track this, to make it available to external users of the lib.
        # e.g. they may want to call send_to_pagerduty() directly if RiemannError is raised.
        self.alert_message = message

        # check if notifications for this host are disabled, and bail if so
        if self.datastore and 'redis' in self.datastore:
            if not self.redis_config:
                logging.error("must call redis_config(), first")
            elif self.check_redis_alerts_disabled(message):
                logging.info("alerting disabled, supressing alert for: %s, %s" % (message['host'], message['plugin']))
                return None

        # get last_state:
        read_state = self.get_current_state()
        try:
            state = json.loads(read_state)
        except ValueError as err:
            # can't JSON decode it? May be old format, or had none existing. That's OK.
            state = {}

        if state is None or state == {}:
            # state file didn't exist - first-run of this check, so don't alert if it's 'ok'
            if 'ok' not in message['severity']:
                state = 'transitioned'
            else:
                state = {}

            message['time'] = now

        # so, we have a valid state file. now check the severity AND the text of the message - if they
        # are identical, everything is still the same. If they changed, we have a state transition to alert on.
        elif message.get('message', ' ') not in state.get('message', '') and self.alert_on_status_string_changes:
            # the message changed, and the state is not OK. So update it.
            if 'ok' not in message['severity']:
                state = 'transitioned'
            message['time'] = now

        # perhaps people aren't using unique error messages, only state. that's OK, we'll trigger
        # on state-only changes, of course:
        elif (severity not in state.get('severity', '')):
            # doesn't match? the message AND severity changed
            state = 'transitioned'
            message['time'] = now

        # if we're not updating the time, add the old one back to the new message, which will get
        # written to the state file:
        if 'time' not in message:
            message['time'] = state.get('time', now)

        # make available externally
        self.cur_state = state

        # write the current state (every time!):
        with open(self.state_file, 'w') as fh:
            fh.write(json.dumps(message))

        # if paging was requested, do it, unless the state is the same as last time
        if page and 'transitioned' in state and not self.no_alerts:
            if not self.pagerduty_key:
                logging.error("must call set_pagerduty_key(), first")
            else:
                self.send_to_pagerduty(message)

        # only email if state is new since last time
        if email and 'transitioned' in state and not self.no_alerts:
            self._send_to_email(email, message)

        # if 'url' was requested, always post to it regardless of state
        if url:
            self._post_to_url(message, url)

        # if 'riemann' was requested, always send the event to riemann
        #
        if riemann:
            self._send_to_riemann(riemann, message)

    def set_pagerduty_key(self, key):
        self.pagerduty_key = key

    def riemann_tag(self, string):
        """
        Adds a string to the rimann_tags list.
        """
        self.riemann_tags.append(string)

    def _send_to_riemann(self, riemann, message):
        """
        Sends the event to riemann, raises RiemannError if it doesn't work.
        """
        if 'host' not in riemann or 'port' not in riemann:
            raise RiemannError("must call riemann_config() first")
        try:
            riemann = bernhard.Client(host=riemann.get('host'), port=riemann.get('port'))
            riemann.send({'host': message['host'],
                          'service': message['plugin'],
                          'state': message['severity'],
                          'description': message['message'],
                          'tags': self.riemann_tags,
                          })
        except:
            e = sys.exc_info()[0]
            raise RiemannError(str(e) + str(message))

    def send_to_pagerduty(self, message, key=None):
        """
        Sends alert to pager duty - you must call authenticate() first
        """
        # if not already done, call config function to set defaults
        if not self.pagerduty_configured:
            if self.redis_config:
                self.set_pagerduty_store('redis', self.redis_config)
            elif self.state_dir:
                self.set_pagerduty_store('file', self.state_dir.rstrip('/') + "/incident_keys")

        # if we called this with a key=, we're wanting to use a different API key for this send.
        if key is not None:
            pagerduty.authenticate(key)
        else:
            pagerduty.authenticate(self.pagerduty_key)

        send_string = "%s: %s %s: %s" % (message['severity'].upper(), message['host'], message['plugin'], message['message'])

        if 'okay' in message['severity']:
            pagerduty.event('resolve', send_string)

        elif 'failure' or 'warning' in message['serverity']:
            pagerduty.event('trigger', send_string)

    def _send_to_socket(self, message, host, port):
        """
        Sends message to host/port via tcp
        """
        sock = socket.socket()

        sock.connect((host, int(port)))
        sock.sendall(message)
        sock.close()

    def _post_to_url(self, message, url):
        """
        HTTP POSTs message to url
        """
        req = urllib2.Request(url, json.dumps(message), {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        resp = f.read()
        f.close()

        return resp

    def _send_to_email(self, address, message):
        """
        Sends alert via email
        """
        print "emailing: ", address

        alert_subject = "%s %s: %s" % (message['host'], message['plugin'], message['message'])

        me = 'collectd@krux.com'
        you = [address.lstrip().rstrip() for address in address.split(',')]

        msg = MIMEMultipart()
        msg['Subject'] = '[collectd] %s %s' % (message['severity'].upper(), alert_subject)
        msg['From'] = me
        # To: header must be a string, and there must be a whitespace after the comma.
        msg['To'] = ", ".join(you)
        body = MIMEText(str(message))
        msg.attach(body)

        s = smtplib.SMTP('localhost')
        # the call to sendmail, needs 'you' to be a list:
        s.sendmail(me, you, msg.as_string())
        s.quit()


class RiemannError(Exception):

    def __str__(self):
        return self.message
