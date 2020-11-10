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

from pyb42 import errorhandler


class ErrorHandlerTestCase(unittest.TestCase):
    def setUp(self):
        self._processed_errors = []

    def err_callback(self, error):
        self._processed_errors.append(error)

    def test_sync(self):
        eh = errorhandler.ErrorHandler(self.err_callback, False)
        self.assertEqual(len(self._processed_errors), 0)
        eh.put(1)
        eh.put(2)
        self.assertEqual(len(self._processed_errors), 0)
        eh.process_errors()
        self.assertEqual(len(self._processed_errors), 2)
        self.assertEqual(1, self._processed_errors[0])
        self.assertEqual(2, self._processed_errors[1])
        eh.put(3)
        self.assertEqual(len(self._processed_errors), 2)
        eh.process_errors()
        self.assertEqual(len(self._processed_errors), 3)
        self.assertEqual(3, self._processed_errors[2])

    def test_async(self):
        eh = errorhandler.ErrorHandler(self.err_callback, True)
        self.assertEqual(len(self._processed_errors), 0)
        eh.put(1)
        self.assertEqual(len(self._processed_errors), 1)
        self.assertEqual(1, self._processed_errors[0])
        eh.put(2)
        self.assertEqual(len(self._processed_errors), 2)
        self.assertEqual(2, self._processed_errors[1])
        eh.put(3)
        self.assertEqual(len(self._processed_errors), 3)
        self.assertEqual(3, self._processed_errors[2])


class ErrorHandlerErrorsTestCase(unittest.TestCase):
    def test_callback(self):
        # invalid callback type
        self.assertRaises(TypeError, errorhandler.ErrorHandler, 'foo')
