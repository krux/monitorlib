### -*- coding: utf-8 -*-
###
### © 2012 Krux Digital, Inc.
### Author: Paul Lathrop <paul@krux.com>
###
import os
from pip.req    import parse_requirements
from setuptools import setup, find_packages

# We want to install all the dependencies of the library as well, but we
# don't want to duplicate the dependencies both here and in
# requirements.pip. Instead we parse requirements.pip to pull in our
# dependencies.
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS = os.path.join(BASE_DIR, 'requirements.pip')

# A requirement file can contain comments (#) and can include some other
# files (--requirement or -r), so we need to use pip's parser to get the
# final list of dependencies.
DEPENDENCIES = [unicode(package.req)
                for package in parse_requirements(REQUIREMENTS)]

setup(name='monitorlib',
      version="0.2.12",
      description='Library for creating monitoring scripts/plugins',
      author='Paul Lathrop, Charlie Schluting',
      author_email='paul@krux.com, charlie@krux.com',
      url='https://github.com/krux/monitorlib',
      install_requires = DEPENDENCIES,
      packages=find_packages(),
      tests_require=['nose', 'coverage'],
      )
