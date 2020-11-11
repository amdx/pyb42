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
import time
from queue import Queue, Empty

try:
    import serialdummy
except ImportError:
    from . import serialdummy

from pyb42 import b42handler

b42handler.logger.disabled = True
b42handler.serial = serialdummy.SerialModule


def get_from_q(q):
    try:
        item = q.get(timeout=0.1)
    except Empty:
        return None
    return item


class B42HandlerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._board = serialdummy.SerialClass()
        cls._b42 = None

    def tearDown(self):
        if self._b42:
            self._b42.stop()
            self._b42 = None

    def send_command(self, command, data=None):
        num_bytes = len(data) if data else 0
        self._board.board_write_byte(command | (num_bytes << 4))
        if num_bytes:
            for i, d in enumerate(data):
                self._board.board_write_byte(d | ((i + 1) << 6))

    def check_sent_frame(self, data):
        seq_num = 0
        num_bytes = -1
        for d in data:
            sent_data = self._board.board_read_byte(timeout=0.1)
            self.assertIsNotNone(sent_data)
            sent_seq_num = sent_data >> 6
            self.assertEqual(sent_seq_num, seq_num)
            if seq_num == 0:
                num_bytes = (sent_data >> 4) & 0x03
                self.assertEqual(sent_data & 0x0F, d)
            else:
                self.assertLessEqual(sent_seq_num, num_bytes)
                self.assertEqual(sent_data & 0x3F, d)
            seq_num += 1

    def check_received_frame(self, rx_q, timestamp, command, data=None):
        rx_frame = get_from_q(rx_q)
        self.assertIsNotNone(rx_frame)
        self.assertIsInstance(rx_frame, b42handler.B42Frame)
        self.assertGreater(rx_frame.timestamp, timestamp)
        self.assertLessEqual(rx_frame.timestamp, time.time())
        self.assertEqual(rx_frame.command, command)
        self.assertEqual(rx_frame.data, data)

    def test_convert(self):
        encode = b42handler.B42Handler.encode_value
        decode = b42handler.B42Handler.decode_value

        def test_value(value, length):
            bytes_ = encode(value, length)
            value_ = decode(*bytes_)
            self.assertEqual(value, value_)

        # one B42 byte sequences
        test_value(0, 1)
        test_value(1, 1)
        test_value(63, 1)
        # two B42 bytes sequences
        test_value(0, 2)
        test_value(1, 2)
        test_value(63, 2)
        test_value(64, 2)
        test_value(4095, 2)
        # three B42 bytes sequences
        test_value(0, 3)
        test_value(1, 3)
        test_value(63, 3)
        test_value(64, 3)
        test_value(4095, 3)
        test_value(4096, 3)
        test_value(262143, 3)
        # truncating
        self.assertEqual(encode(64, 1), (0x00,))
        self.assertEqual(encode(65, 1), (0x01,))
        self.assertEqual(encode(4096, 2), (0x00, 0x00))
        self.assertEqual(encode(4097, 2), (0x00, 0x01))
        self.assertEqual(encode(262144, 3), (0x00, 0x00, 0x00))
        self.assertEqual(encode(262145, 3), (0x00, 0x00, 0x01))

    def test_send(self):
        self._b42 = b42handler.B42Handler()
        self._b42.send_frame(0x01)
        self.check_sent_frame((0x01,))
        self._b42.send_frame(0x02, 1)
        self.check_sent_frame((0x02, 1))
        self._b42.send_frame(0x03, 1, 2)
        self.check_sent_frame((0x03, 1, 2))
        self._b42.send_frame(0x04, 1, 2, 3)
        self.check_sent_frame((0x4, 1, 2, 3))

    def test_recv(self):
        rx_q = Queue()
        self._b42 = b42handler.B42Handler(rx_frame_q=rx_q)
        now = time.time()
        self.send_command(0x01)
        self.check_received_frame(rx_q, now, 0x01)
        self.send_command(0x02, (1,))
        self.check_received_frame(rx_q, now, 0x02, (1,))
        self.send_command(0x03, (1, 2))
        self.check_received_frame(rx_q, now, 0x03, (1, 2))
        self.send_command(0x04, (1, 2, 3))
        self.check_received_frame(rx_q, now, 0x04, (1, 2, 3))


class B42HandlerErrorsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._board = serialdummy.SerialClass()
        cls._b42 = None

    def tearDown(self):
        if self._b42:
            self._b42.stop()
            self._b42 = None

    def send_bytes(self, data):
        for d in data:
            self._board.board_write_byte(d)

    def check_error(self, rx_q, err_q, timestamp, code):
        rx_error = get_from_q(err_q)
        self.assertIsNotNone(rx_error)
        self.assertIsInstance(rx_error, b42handler.B42Error)
        self.assertEqual(rx_q.qsize(), 0)
        self.assertGreater(rx_error.timestamp, timestamp)
        self.assertLessEqual(rx_error.timestamp, time.time())
        self.assertEqual(rx_error.code, code)

    def test_convert(self):
        self.assertRaises(ValueError, b42handler.B42Handler.encode_value, 0x00, 0)
        self.assertRaises(ValueError, b42handler.B42Handler.encode_value, 0x00, 4)
        self.assertRaises(ValueError, b42handler.B42Handler.decode_value)
        self.assertRaises(ValueError, b42handler.B42Handler.decode_value, 0x00, 0x01, 0x02, 0x3)

    def test_send(self):
        self._b42 = b42handler.B42Handler()
        # invalid command (out of range)
        self.assertRaises(ValueError, self._b42.send_frame, 0x00)
        self.assertRaises(ValueError, self._b42.send_frame, 0x10)
        # invalid data (out of range)
        self.assertRaises(ValueError, self._b42.send_frame, 0x01, -1)
        self.assertRaises(ValueError, self._b42.send_frame, 0x01, 0x40)
        self.assertRaises(ValueError, self._b42.send_frame, 0x02, 1, 0x40)
        self.assertRaises(ValueError, self._b42.send_frame, 0x03, 1, 2, 0x40)
        # too many data bytes
        self.assertRaises(ValueError, self._b42.send_frame, 0x04, 1, 2, 3, 4)

    def test_recv(self):
        rx_q = Queue()
        err_q = Queue()
        self._b42 = b42handler.B42Handler(rx_frame_q=rx_q, rx_error_q=err_q)
        now = time.time()
        # zero byte
        self.send_bytes((0x00,))
        self.check_error(rx_q, err_q, now, b42handler.B42_ERROR_ZERO_BYTE)
        # command byte expected
        self.send_bytes((0x81,))
        self.check_error(rx_q, err_q, now, b42handler.B42_ERROR_EXPECT_COMMAND)
        # data byte expected (with correct sequence number)
        self.send_bytes((0x11, 0xFF))
        self.check_error(rx_q, err_q, now, b42handler.B42_ERROR_EXPECT_DATA1)
        self.send_bytes((0x21, 0x41, 0x42))
        self.check_error(rx_q, err_q, now, b42handler.B42_ERROR_EXPECT_DATA2)
        self.send_bytes((0x31, 0x41, 0x82, 0x83))
        self.check_error(rx_q, err_q, now, b42handler.B42_ERROR_EXPECT_DATA3)

    def test_resync(self):
        rx_q = Queue()
        err_q = Queue()
        self._b42 = b42handler.B42Handler(rx_frame_q=rx_q, rx_error_q=err_q)
        now = time.time()
        self.send_bytes((0x11,))  # expects 1 data byte
        self.send_bytes((0x21, 0x41, 0x82))  # sequence error, but start of new frame
        rx_frame = get_from_q(rx_q)
        self.assertIsNotNone(rx_frame)
        self.assertEqual(rx_frame.command, 0x01)
        self.assertEqual(rx_frame.data, (0x01, 0x02))
        self.check_error(rx_q, err_q, now, b42handler.B42_ERROR_EXPECT_DATA1)
