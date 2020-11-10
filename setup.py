#!/usr/bin/env python
# -*- coding: utf-8 -*-

# B42 protocol library
#
# Copyright (C) 2020 Archimedes Exhibitions GmbH
# All rights reserved.
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
# to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from setuptools import setup, find_packages
from pathlib import Path


def load_version():
    version = {}
    with open(str(here / NAME / '__version__.py'), 'r') as fp:
        exec(fp.read(), version)
    return version['__version__']


def load_readme():
    with open(str(here / 'README.md'), 'r') as fp:
        readme = fp.read()
    return readme, 'text/markdown'


here = Path(__file__).absolute().parent

NAME = 'pyb42'
VERSION = load_version()
LONG_DESC, LONG_DESC_CONTENT_TYPE = load_readme()
PACKAGES = find_packages()

setup(
    name=NAME,
    version=VERSION,
    description='B42 serial protocol library',
    long_description=LONG_DESC,
    long_description_content_type=LONG_DESC_CONTENT_TYPE,
    author='Archimedes Exhibitions GmbH',
    author_email='circuit@amdx.de',
    url='https://github.com/amdx/',
    packages=PACKAGES,
    python_requires='>=3.5',
    install_requires=['pyserial==3.4'],
    test_suite='tests'
)
