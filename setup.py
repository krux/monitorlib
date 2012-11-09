### -*- coding: utf-8 -*-
###
### © 2012 Krux Digital, Inc.
### Author: Paul Lathrop <paul@krux.com>
###

from setuptools import setup, find_packages

setup(name='monitorlib',
      version="0.1.7",
      description='Library for creating monitoring scripts/plugins',
      author='Paul Lathrop, Charlie Schluting',
      author_email='paul@krux.com, charlie@krux.com',
      url='https://github.com/krux/monitorlib',
      packages=find_packages(),
      tests_require=['nose', 'coverage'],
      )
