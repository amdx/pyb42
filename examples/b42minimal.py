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
"""

from queue import Queue
from time import sleep

from pyb42 import B42Handler

# application defined command codes (0x00 is reserved and should not be used)
MYCOMMAND_HELLO = 0x01  # this is a board-to-host only command
MYCOMMAND_STATUS = 0x02
MYCOMMAND_FOO = 0x03
MYCOMMAND_BAR = 0x04
# application defined status/error codes ([0x01..0x0F] used by B42 itself)
MYERROR_NO_ERROR = 0x00
MYERROR_INVALID_LENGTH = 0x10


class B42App:
    def __init__(self, port):
        self.rx_frame_q = Queue()
        self.b42handler = B42Handler(rx_frame_q=self.rx_frame_q, port=port)
        self.b42handler.reset()  # manual reset necessary for some boards

        self.is_done = False

    def main_loop(self):
        def process_rx_frame():
            while self.rx_frame_q.empty():
                sleep(0.1)

            rx_frame = self.rx_frame_q.get()
            if rx_frame.command == MYCOMMAND_HELLO:
                self.on_hello(rx_frame)
            elif rx_frame.command == MYCOMMAND_STATUS:
                self.on_status(rx_frame)
            elif rx_frame.command == MYCOMMAND_FOO:
                self.on_foo(rx_frame)
            elif rx_frame.command == MYCOMMAND_BAR:
                self.on_bar(rx_frame)
            else:
                print('Received unknown command:', rx_frame)

        process_rx_frame()  # HELLO

        print('Requesting STATUS')
        self.b42handler.send_frame(MYCOMMAND_STATUS)
        process_rx_frame()  # STATUS

        print('Requesting three FOO counts')
        self.b42handler.send_frame(MYCOMMAND_FOO)
        self.b42handler.send_frame(MYCOMMAND_FOO)
        self.b42handler.send_frame(MYCOMMAND_FOO)
        process_rx_frame()  # 1st FOO
        process_rx_frame()  # 2nd FOO
        process_rx_frame()  # 3rd FOO

        print('Setting BAR to 1 (the on-board LED should light up)')
        self.b42handler.send_frame(MYCOMMAND_BAR, 1)
        process_rx_frame()  # BAR

        print('Do intentional harm to provoke an error (invalid command)')
        self.b42handler.send_frame(0x0F)
        print('Do intentional harm to provoke an error (invalid data length)')
        self.b42handler.send_frame(MYCOMMAND_STATUS, 0)
        while not self.is_done:
            process_rx_frame()  # 2 x STATUS

    def on_hello(self, rx_frame):
        print('The board has woken up and says hello')

    def on_status(self, rx_frame):
        print('Received a STATUS command with data:', rx_frame.data)
        if rx_frame.data[0] == MYERROR_INVALID_LENGTH:
            print('Marking app done')
            self.is_done = True

    def on_foo(self, rx_frame):
        print('FOO reply data:', rx_frame.data)

    def on_bar(self, rx_frame):
        print('BAR reply data:', rx_frame.data)


if __name__ == '__main__':
    import sys

    port = sys.argv[1] if 1 < len(sys.argv) else B42Handler.DEFAULT_PORT
    app = B42App(port)

    print('--- App is starting up, waiting for completion ---')
    app.main_loop()
    print('--- App has finished ---')
