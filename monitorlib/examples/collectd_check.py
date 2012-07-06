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


    if check_value:
        print collectd.ok("everything is fine", pageme=True)

    elif check_value is False:
        print collectd.warning("something looks strange", False, email=['charlie@krux.com'])

    elif check_value is None:
        print collectd.failure("something is definitely broken", page=True, email=['charlie@krux.com'])

    # output a metric:
    print collectd.metric("testing/service_bar", 5)


