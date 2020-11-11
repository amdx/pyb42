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

"""
Shows how to interact with a microcontroller board via the B42 protocol.

HOST (computer) <--- B42 ---> BOARD (e.g. Arduino)

The serial endpoint can be an Arduino compatible board, programmed with the
B42 minimal example firmware from https://github.com/amdx/b42lib.

This example runs with asynchronous command dispatching. The callbacks
are executed in B42Handler's receiver thread context - watch out for thread
safety in your business logic.
"""

from pyb42 import B42Handler
from pyb42 import CommandHandler

# application defined command codes (0x00 is reserved and should not be used)
MYCOMMAND_HELLO = 0x01  # this is a board-to-host only command
MYCOMMAND_STATUS = 0x02
MYCOMMAND_FOO = 0x03
MYCOMMAND_BAR = 0x04
# application defined status/error codes ([0x01..0x0F] used by B42 itself)
MYERROR_NO_ERROR = 0x00
MYERROR_INVALID_LENGTH = 0x10


class B42AsyncApp:
    def __init__(self, port):
        commandhandler = CommandHandler(async_dispatch=True)
        commandhandler.register_command(MYCOMMAND_HELLO, self.on_hello, 0)
        commandhandler.register_command(MYCOMMAND_STATUS, self.on_status, 1)
        commandhandler.register_command(MYCOMMAND_FOO, self.on_foo, 1)
        commandhandler.register_command(MYCOMMAND_BAR, self.on_bar, 1)

        self.b42handler = B42Handler(rx_frame_q=commandhandler, port=port)
        self.b42handler.reset()  # manual reset necessary for some boards

        self.is_done = False

    def on_hello(self, timestamp, data):
        print('The board has woken up and says hello')

        print('Requesting STATUS')
        self.b42handler.send_frame(MYCOMMAND_STATUS)

        print('Requesting three FOO counts')
        self.b42handler.send_frame(MYCOMMAND_FOO)
        self.b42handler.send_frame(MYCOMMAND_FOO)
        self.b42handler.send_frame(MYCOMMAND_FOO)

        print('Setting BAR to 1 (the on-board LED should light up)')
        self.b42handler.send_frame(MYCOMMAND_BAR, 1)

        print('Do intentional harm to provoke an error (invalid command)')
        self.b42handler.send_frame(0x0F)
        print('Do intentional harm to provoke an error (invalid data length)')
        self.b42handler.send_frame(MYCOMMAND_STATUS, 0)

    def on_status(self, timestamp, data):
        print('Received a STATUS command with data:', data)
        if data[0] == MYERROR_INVALID_LENGTH:
            print('Marking app done')
            self.is_done = True

    def on_foo(self, timestamp, data):
        print('FOO reply data:', data)

    def on_bar(self, timestamp, data):
        print('BAR reply data:', data)


if __name__ == '__main__':
    import sys
    from time import sleep

    port = sys.argv[1] if 1 < len(sys.argv) else B42Handler.DEFAULT_PORT
    app = B42AsyncApp(port)

    print('--- App is starting up, waiting for completion ---')
    while not app.is_done:
        sleep(0.5)
    print('--- App has finished ---')
