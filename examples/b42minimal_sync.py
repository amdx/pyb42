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

This example runs with synchronous command dispatching. The callbacks are
executed in the thread context of the dispatch_commands() caller (probably
the application main loop).
"""

from time import sleep

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
        self.commandhandler = CommandHandler(async_dispatch=False)
        self.commandhandler.register_command(MYCOMMAND_HELLO, self.on_hello, 0)
        self.commandhandler.register_command(MYCOMMAND_STATUS, self.on_status, 1)
        self.commandhandler.register_command(MYCOMMAND_FOO, self.on_foo, 1)
        self.commandhandler.register_command(MYCOMMAND_BAR, self.on_bar, 1)

        self.b42handler = B42Handler(rx_frame_q=self.commandhandler, port=port)
        self.b42handler.reset()  # manual reset necessary for some boards

        self.hello_done = False
        self.status_done = False
        self.num_foo_done = 0
        self.bar_done = False
        self.harm_done = False

    def main_loop(self):
        def wait_dispatch(message, condition):
            input('> Hit <RETURN> to dispatch pending commands (%s) ' % message)
            self.commandhandler.dispatch_commands()
            while not condition():
                sleep(0.1)
                self.commandhandler.dispatch_commands()

        wait_dispatch('HELLO', lambda: self.hello_done)

        print('Requesting STATUS')
        self.b42handler.send_frame(MYCOMMAND_STATUS)
        wait_dispatch('STATUS', lambda: self.status_done)

        print('Requesting three FOO counts')
        self.b42handler.send_frame(MYCOMMAND_FOO)
        self.b42handler.send_frame(MYCOMMAND_FOO)
        self.b42handler.send_frame(MYCOMMAND_FOO)
        wait_dispatch('3 x FOO', lambda: self.num_foo_done == 3)

        print('Setting BAR to 1 (the on-board LED should light up)')
        self.b42handler.send_frame(MYCOMMAND_BAR, 1)
        wait_dispatch('BAR', lambda: self.bar_done)

        print('Do intentional harm to provoke an error (invalid command)')
        self.b42handler.send_frame(0x0F)
        print('Do intentional harm to provoke an error (invalid data length)')
        self.b42handler.send_frame(MYCOMMAND_STATUS, 0)
        wait_dispatch('2 x STATUS', lambda: self.harm_done)

    def on_hello(self, timestamp, data):
        print('The board has woken up and says hello')
        self.hello_done = True

    def on_status(self, timestamp, data):
        print('Received a STATUS command with data:', data)
        self.status_done = True
        if data[0] == MYERROR_INVALID_LENGTH:
            print('Marking app done')
            self.harm_done = True

    def on_foo(self, timestamp, data):
        print('FOO reply data:', data)
        self.num_foo_done += 1

    def on_bar(self, timestamp, data):
        print('BAR reply data:', data)
        self.bar_done = True


if __name__ == '__main__':
    import sys

    port = sys.argv[1] if 1 < len(sys.argv) else B42Handler.DEFAULT_PORT
    app = B42AsyncApp(port)

    print('--- App is starting up, waiting for completion ---')
    app.main_loop()
    print('--- App has finished ---')
