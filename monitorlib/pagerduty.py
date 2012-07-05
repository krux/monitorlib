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

import time
import socket

try:
    import simplejson as json
except ImportError:
    import json

global PD_KEY

def authenticate(key):
    """
    Call this function, and provide your pagerduty service key.
    """
    PD_KEY = key

def get_incident_key(desc):
    """
    Returns an incident key if one matches 'desc', otherwise returns an empty string.
    """
    return ''

def del_incident_key(desc):
    pass

def add_incident_key(desc, key):
    pass

def construct(key, event_type, desc, details):
    """
    Constructs pagerduty json for sending, by looking up the incident_key
    in persistent storage, to see if this is a duplicate.
    """

    return {'service_key': key, 'event_type': event_type,
            'description': desc, 'incident_key': get_incident_key(desc),
            'details': details
           }

def send_to_pagetduty(message):
    """
    Sends message to pagerduty, and records the response's incident_key for later use
    (unless the event_type was 'resolve', then deletes key if it exists).
    """

    pass

def event(event_type, desc, details=None):
    """
    Entry point interface to create a PD event.
    """

    message = construct(PD_KEY, event_type, desc, details)

    if 'resolve' in event_type:
        del_incident_key(desc)

    send_to_pagerduty(message)


