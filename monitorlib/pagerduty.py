#
# Author: Charlie Schluting <charlie@krux.com>
#
"""
    Library to enable sending to pagerduty, and managing state to maintain
    PD's incident_key and avoid duplicates.

    Usage:
    pagerduty.authenticate(key)
    pagerduty.event(event_type, message, [details_json])
"""

import os
import sys
import time
import socket
import urllib2
import cPickle as pickle
try:
    import redis
except ImportError:
    pass

try:
    import simplejson as json
except ImportError:
    import json

def set_datastore(kind, config):
    global KEY_STORAGE
    KEY_STORAGE = kind

    global STORAGE_CONFIG
    STORAGE_CONFIG = config

def authenticate(key):
    """
    Call this function, and provide your pagerduty service key.
    """
    global PD_KEY
    PD_KEY = key

def redis_conn(conf):
    """
    Create and return a redis connection, if you haven't done so already
    """
    global REDIS
    if 'REDIS' not in globals():
        REDIS = redis.Redis(conf['reader'], conf['port'], conf['db'], conf['passwd'], socket_timeout=2)

    return REDIS

def get_incident_key(store_key):
    """
    Returns an incident key if one matches 'desc', otherwise returns an empty string.
    """
    if 'file' in KEY_STORAGE:
        if not os.path.exists(STORAGE_CONFIG):
            return None

        try:
            keys = pickle.load(open(STORAGE_CONFIG, 'r'))
        except EOFError:
            return None

        return keys.get(store_key)

    elif 'redis' in KEY_STORAGE:
        conn = redis_conn(STORAGE_CONFIG)
        return conn.get(store_key)

def del_incident_key(store_key):
    """
    Removes an incident key from key storage
    """
    if 'file' in KEY_STORAGE:
        try:
            keys = pickle.load(open(STORAGE_CONFIG, 'r'))
        except EOFError:
            return None

        del keys[store_key]
        pickle.dump(keys, open(STORAGE_CONFIG, 'w'))

    elif 'redis' in KEY_STORAGE:
        conn = redis_conn(STORAGE_CONFIG)
        return conn.delete(store_key)

def add_incident_key(store_key, incident_key):
    """
    Adds an incident key to key storage
    """
    if 'file' in KEY_STORAGE:
        if not os.path.exists(STORAGE_CONFIG):
            fh = open(STORAGE_CONFIG, 'w')
            pickle.dump({}, fh)
            fh.close

        try:
            keys = pickle.load(open(STORAGE_CONFIG, 'r'))
        except EOFError:
            keys = {}

        keys.update({store_key: incident_key})
        pickle.dump(keys, open(STORAGE_CONFIG, 'w'))

    elif 'redis' in KEY_STORAGE:
        conn = redis_conn(STORAGE_CONFIG)
        return conn.set(store_key, incident_key)

def construct(service_key, event_type, desc, store_key, details):
    """
    Constructs pagerduty json for sending, by looking up the incident_key
    in persistent storage, to see if this is a duplicate.
    """

    return {'service_key': service_key, 'event_type': event_type,
            'description': desc, 'incident_key': get_incident_key(store_key),
            'details': details
           }

def send_to_pagerduty(message):
    """
    Sends message to pagerduty, and records the response's incident_key for later use
    (unless the event_type was 'resolve', then deletes key if it exists).
    """

    pd_url = 'https://events.pagerduty.com/generic/2010-04-15/create_event.json'

    req = urllib2.Request(pd_url, json.dumps(message), {'Content-Type': 'application/json'})
    f = urllib2.urlopen(req)
    resp = f.read()
    f.close()

    return resp

def event(event_type, desc, details=None):
    """
    Entry point interface to create a PD event.
    """
    # the host & script name from the alert message:
    host_script = desc.split(':')[0]

    message = construct(PD_KEY, event_type, desc, host_script, details)

    # is this is an OKAY message, don't send to PD unless we have an incident key:
    if 'resolve' in event_type and message['incident_key']:
        resp = json.loads(send_to_pagerduty(message))
    elif 'trigger' in event_type:
        resp = json.loads(send_to_pagerduty(message))
    else:
        print message
        print "nothing to do"
        sys.exit(0)

    # Response from PD: {"status":"success","message":"Event processed","incident_key":"74c804e0a92c012fdea322000af842a7"}
    if 'resolve' in event_type:
        del_incident_key(host_script)
    else:
        add_incident_key(host_script, resp['incident_key'])



