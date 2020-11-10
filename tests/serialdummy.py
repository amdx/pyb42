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

# Hook to simulate serial.Serial

import time
from queue import Queue


class SerialClass:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls, *args, **kwargs)
        return cls.__instance

    def __init__(self, *args, **kwargs):
        self._timeout = kwargs.get('timeout', None)
        self._host2board_q = Queue()
        self._board2host_q = Queue()

    # host side interface (pySerial API) - used by B42Handler #

    @property
    def port(self):
        return 'serialdummy'

    def close(self):
        self._host2board_q = Queue()
        self._board2host_q = Queue()

    def write(self, data):
        self._host2board_q.put(data)
        return len(data)

    def read(self):
        if self._timeout is not None:
            timeout = time.time() + self._timeout
            while self._board2host_q.empty():
                if timeout <= time.time():
                    return b''
        else:  # blocking
            while self._board2host_q.empty():
                pass
        return self._board2host_q.get()

    # board side interface - used by tests #

    def board_write_byte(self, byte):
        self._board2host_q.put(bytes((byte,)))

    def board_read_byte(self, timeout=None):
        if timeout is not None:
            timeout += time.time()
            while self._host2board_q.empty():
                if timeout <= time.time():
                    return None
        else:  # blocking
            while self._host2board_q.empty():
                pass
        return self._host2board_q.get()[0]


class SerialModule:
    Serial = SerialClass

    @staticmethod
    def serial_for_url(*args, **kwargs):
        return SerialClass(*args, **kwargs)
