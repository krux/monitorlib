#
# Author: Charlie Schluting <charlie@krux.com>
#
"""
    Library to enable sending to pagerduty, and managing state to maintain
    PD's incident_key and avoid duplicates.

    Usage:
    pagerduty.authenticate(key)
    pageduty.set_datastore('file', '/tmp/incident_keys') # or 'redis' - see collectd.py
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
    """
    sets datastore type and config
    """
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

def redis_conn(conf, mode):
    """
    Create and return a redis connection, if you haven't done so already
    """
    global REDIS_READER
    global REDIS_WRITER
    if 'read' in mode:
        if 'REDIS_READER' not in globals():
            REDIS_READER = redis.Redis(conf['reader'], conf['reader_port'], conf['db'], conf['passwd'], socket_timeout=2)
        return REDIS_READER
    elif 'write' in mode:
        if 'REDIS_WRITER' not in globals():
            REDIS_WRITER = redis.Redis(conf['writer'], conf['writer_port'], conf['db'], conf['passwd'], socket_timeout=2)
        return REDIS_WRITER

def get_incident_key(store_key):
    """
    Returns an incident key if one matches 'store_key', otherwise returns None.
    """
    if 'file' in KEY_STORAGE:
        if not os.path.exists(STORAGE_CONFIG):
            return None

        try:
            keys = pickle.load(open(STORAGE_CONFIG, 'r'))
        except EOFError:
            # empty file?
            return None

        return keys.get(store_key)

    elif 'redis' in KEY_STORAGE:
        conn = redis_conn(STORAGE_CONFIG, 'read')
        return conn.get(store_key)

def del_incident_key(store_key):
    """
    Removes an incident_key from key storage
    """
    if 'file' in KEY_STORAGE:
        try:
            keys = pickle.load(open(STORAGE_CONFIG, 'r'))
        except EOFError:
            return None

        del keys[store_key]
        pickle.dump(keys, open(STORAGE_CONFIG, 'w'))

    elif 'redis' in KEY_STORAGE:
        conn = redis_conn(STORAGE_CONFIG, 'write')
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
        conn = redis_conn(STORAGE_CONFIG, 'write')
        return conn.set(store_key, incident_key)

def construct(service_key, event_type, desc, store_key, details):
    """
    Constructs pagerduty json for sending; looks up the incident_key
    in persistent storage, and adds it.
    """

    return {'service_key': service_key, 'event_type': event_type,
            'description': desc, 'incident_key': get_incident_key(store_key),
            'details': details
           }

def send_to_pagerduty(message):
    """
    Sends message to pagerduty, returns the response.
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
    # store the API key as part of the thing to key off of when storing incident_keys, to support multiple API keys at once.
    storage_key = PD_KEY + '^' + host_script

    message = construct(PD_KEY, event_type, desc, storage_key, details)

    # if this is an OKAY message, don't send to PD unless we have an incident key:
    if 'resolve' in event_type and message['incident_key']:
        resp = json.loads(send_to_pagerduty(message))
    elif 'trigger' in event_type:
        resp = json.loads(send_to_pagerduty(message))
    else:
        # it was a 'resolve' and we didn't have the incident_key already (can't delete). done.
        return None

    # Response from PD: {"status":"success","message":"Event processed","incident_key":"74c804e0a92c012fdea322000af842a7"}
    if 'resolve' in event_type:
        # don't care what the response was - just make sure to remove it from KEY_STORAGE
        del_incident_key(storage_key)
    else:
        # store the incident_key returned by pagerduty
        add_incident_key(storage_key, resp['incident_key'])



