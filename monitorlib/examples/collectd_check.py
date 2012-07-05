#!/usr/bin/env kpython
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
    check_value = None


    if check_value:
        print collectd.ok("everything is fine")

    elif check_value is False:
        print collectd.warning("something looks strange")

    elif check_value is None:
        print collectd.failure("something is definitely broken", pageme=True)

    # output a metric:
    print collectd.metric("testing/service_bar", 5)


