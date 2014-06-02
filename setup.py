### -*- coding: utf-8 -*-
###
### © 2012, 2014 Krux Digital, Inc.
### Author: Charlie Schluting <charlie@krux.com>
###

from setuptools import setup, find_packages


setup(
    name='monitorlib',
    version="0.2.16",
    description='Library for creating monitoring scripts/plugins',
    author='Charlie Schluting',
    author_email='charlie@krux.com',
    url='https://github.com/krux/monitorlib',
    packages=find_packages(),
    tests_require=['nose', 'coverage'],
)
