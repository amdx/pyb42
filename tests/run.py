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

import unittest
import sys
sys.path.insert(0, '..')

import test_b42handler
import test_commandhandler

testLoader = unittest.TestLoader()
suite = unittest.TestSuite()
suite.addTest(testLoader.loadTestsFromModule(test_b42handler))
suite.addTest(testLoader.loadTestsFromModule(test_commandhandler))


# implements the unittest load_tests protocol
def load_tests(loader, tests, pattern):
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)
