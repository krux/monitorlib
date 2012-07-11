#!/usr/local/bin/kpython
#
# Author: Charlie Schluting <charlie@krux.com>
#

"""
    Sample script implementing a collectd check using monitorlib.

"""
import os
import sys
import monitorlib.collectd as collectd

if __name__ == '__main__':

    # fake a check, that outputs True/False:
    check_value = False

    # enable datastore checking (for host alerts being disabled, also uses redis to store
    # pagerduty state info):
    collectd.set_redis_config('write-host', 'read-host', 6379, 6379, 'password', 'db0')

    # enable pagerduty:
    collectd.set_pagerduty_key('key....')

    if check_value:
        collectd.ok("everything is fine", page=True)

    elif check_value is False:
        collectd.warning("something looks strange", False, email='charlie@krux.com')

    elif check_value is None:
        collectd.failure("something is definitely broken", page=True)

    # output a metric:
    print collectd.metric("testing/counter", 5)


