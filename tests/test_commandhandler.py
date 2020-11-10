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
from queue import Queue

from pyb42 import commandhandler

commandhandler.logger.disabled = True


class CommandHandlerTestCase(unittest.TestCase):
    def setUp(self):
        self._dispatched_commands = []

    def cmd_callback(self, command, timestamp, data):
        self._dispatched_commands.append((timestamp, command, data))

    def cmd_callback1(self, timestamp, data):
        self.cmd_callback(0x01, timestamp, data)

    def cmd_callback2(self, timestamp, data):
        self.cmd_callback(0x02, timestamp, data)

    def test_commands_sync(self):
        ch = commandhandler.CommandHandler(None, False)
        ch.register_command(0x01, self.cmd_callback1)
        ch.register_command(0x02, self.cmd_callback2)
        self.assertEqual(len(self._dispatched_commands), 0)
        ch.put(commandhandler.B42Frame(1, 0x01, None))
        ch.put(commandhandler.B42Frame(2, 0x01, (1, 2, 3)))
        self.assertEqual(len(self._dispatched_commands), 0)
        ch.dispatch_commands()
        self.assertEqual(len(self._dispatched_commands), 2)
        self.assertEqual((1, 0x01, None), self._dispatched_commands[0])
        self.assertEqual((2, 0x01, (1, 2, 3)), self._dispatched_commands[1])
        ch.put(commandhandler.B42Frame(3, 0x02, (0,)))
        self.assertEqual(len(self._dispatched_commands), 2)
        ch.dispatch_commands()
        self.assertEqual(len(self._dispatched_commands), 3)
        self.assertEqual((3, 0x02, (0,)), self._dispatched_commands[2])

    def test_commands_async(self):
        ch = commandhandler.CommandHandler(None, True)
        ch.register_command(0x01, self.cmd_callback1)
        ch.register_command(0x02, self.cmd_callback2)
        self.assertEqual(len(self._dispatched_commands), 0)
        ch.put(commandhandler.B42Frame(1, 0x01, None))
        self.assertEqual(len(self._dispatched_commands), 1)
        self.assertEqual((1, 0x01, None), self._dispatched_commands[0])
        ch.put(commandhandler.B42Frame(2, 0x01, (1, 2, 3)))
        self.assertEqual(len(self._dispatched_commands), 2)
        self.assertEqual((2, 0x01, (1, 2, 3)), self._dispatched_commands[1])
        ch.put(commandhandler.B42Frame(3, 0x02, (0,)))
        self.assertEqual(len(self._dispatched_commands), 3)
        self.assertEqual((3, 0x02, (0,)), self._dispatched_commands[2])

    def test_num_data(self):
        ch = commandhandler.CommandHandler(None, True)
        ch.register_command(0x00, lambda t, d: self.cmd_callback(0x00, t, d), 0)
        ch.register_command(0x01, lambda t, d: self.cmd_callback(0x01, t, d), 1)
        ch.register_command(0x02, lambda t, d: self.cmd_callback(0x02, t, d), 2)
        ch.register_command(0x03, lambda t, d: self.cmd_callback(0x03, t, d), 3)
        ch.register_command(0x04, lambda t, d: self.cmd_callback(0x04, t, d), (0, 1, 2, 3))
        ch.put(commandhandler.B42Frame(1, 0x00, None))
        self.assertEqual((1, 0x00, None), self._dispatched_commands[0])
        ch.put(commandhandler.B42Frame(2, 0x01, (1,)))
        self.assertEqual((2, 0x01, (1,)), self._dispatched_commands[1])
        ch.put(commandhandler.B42Frame(3, 0x02, (1, 2)))
        self.assertEqual((3, 0x02, (1, 2)), self._dispatched_commands[2])
        ch.put(commandhandler.B42Frame(4, 0x03, (1, 2, 3)))
        self.assertEqual((4, 0x03, (1, 2, 3)), self._dispatched_commands[3])
        ch.put(commandhandler.B42Frame(5, 0x04, None))
        self.assertEqual((5, 0x04, None), self._dispatched_commands[4])
        ch.put(commandhandler.B42Frame(6, 0x04, (1,)))
        self.assertEqual((6, 0x04, (1,)), self._dispatched_commands[5])
        ch.put(commandhandler.B42Frame(7, 0x04, (1, 2)))
        self.assertEqual((7, 0x04, (1, 2)), self._dispatched_commands[6])
        ch.put(commandhandler.B42Frame(8, 0x04, (1, 2, 3)))
        self.assertEqual((8, 0x04, (1, 2, 3)), self._dispatched_commands[7])


class CommandHandlerErrorsTestCase(unittest.TestCase):
    def setUp(self):
        self._num_dispatched = 0
        self._error_q = Queue()

    def cmd_callback(self, *_):
        self._num_dispatched += 1

    def check_error(self, timestamp, code):
        self.assertEqual(self._num_dispatched, 0)
        self.assertEqual(self._error_q.qsize(), 1)
        error = self._error_q.get()
        self.assertIsInstance(error, commandhandler.CommandError)
        self.assertEqual(error.timestamp, timestamp)
        self.assertEqual(error.code, code)

    def test_register_command(self):
        ch = commandhandler.CommandHandler(None, True)
        # invalid code type
        self.assertRaises(TypeError, ch.register_command, 'foo', self.cmd_callback)
        # invalid callback type
        self.assertRaises(TypeError, ch.register_command, 42, 'foo')
        # invalid num_data parameters
        self.assertRaises(TypeError, ch.register_command, 0x01, self.cmd_callback, 'foo')
        self.assertRaises(TypeError, ch.register_command, 0x01, self.cmd_callback, (1, 'foo'))

    def test_unregistered(self):
        ch = commandhandler.CommandHandler(self._error_q, True)
        self.assertTrue(self._error_q.empty())
        # unregistered command
        ch.put(commandhandler.B42Frame(1, 0x01, None))
        self.check_error(1, commandhandler.CMD_ERROR_UNREGISTERED)

    def test_num_data(self):
        ch = commandhandler.CommandHandler(self._error_q, True)
        ch.register_command(0x00, lambda t, d: self.cmd_callback(0x00, t, d), 0)
        ch.register_command(0x01, lambda t, d: self.cmd_callback(0x01, t, d), 1)
        ch.register_command(0x02, lambda t, d: self.cmd_callback(0x02, t, d), 2)
        ch.register_command(0x03, lambda t, d: self.cmd_callback(0x03, t, d), 3)
        ch.register_command(0x10, lambda t, d: self.cmd_callback(0x03, t, d), (0, 2))
        self.assertTrue(self._error_q.empty())
        # no data bytes accepted
        ch.put(commandhandler.B42Frame(1, 0x00, (1,)))
        self.check_error(1, commandhandler.CMD_ERROR_NUM_DATA)
        # 1 data byte accepted
        ch.put(commandhandler.B42Frame(10, 0x01, None))
        self.check_error(10, commandhandler.CMD_ERROR_NUM_DATA)
        ch.put(commandhandler.B42Frame(12, 0x01, (1, 2)))
        self.check_error(12, commandhandler.CMD_ERROR_NUM_DATA)
        # 2 data bytes accepted
        ch.put(commandhandler.B42Frame(20, 0x02, None))
        self.check_error(20, commandhandler.CMD_ERROR_NUM_DATA)
        ch.put(commandhandler.B42Frame(21, 0x02, (1,)))
        self.check_error(21, commandhandler.CMD_ERROR_NUM_DATA)
        ch.put(commandhandler.B42Frame(23, 0x02, (1, 2, 3)))
        self.check_error(23, commandhandler.CMD_ERROR_NUM_DATA)
        # 3 data bytes accepted
        ch.put(commandhandler.B42Frame(30, 0x03, None))
        self.check_error(30, commandhandler.CMD_ERROR_NUM_DATA)
        ch.put(commandhandler.B42Frame(32, 0x03, (1, 2)))
        self.check_error(32, commandhandler.CMD_ERROR_NUM_DATA)
        ch.put(commandhandler.B42Frame(34, 0x03, (1, 2, 3, 4)))
        self.check_error(34, commandhandler.CMD_ERROR_NUM_DATA)
        # 0 or 2 data bytes accepted
        ch.put(commandhandler.B42Frame(41, 0x00, (1,)))
        self.check_error(41, commandhandler.CMD_ERROR_NUM_DATA)
        ch.put(commandhandler.B42Frame(43, 0x02, (1, 2, 3)))
        self.check_error(43, commandhandler.CMD_ERROR_NUM_DATA)
