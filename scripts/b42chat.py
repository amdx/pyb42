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

from argparse import ArgumentParser
from queue import Queue, Empty
from time import sleep

from pyb42 import B42Handler


def parse_cli_args():
    parser = ArgumentParser(
        description='B42 chat tester. Send some test bytes and wait for responses.'
    )
    parser.add_argument('port', help='serial port')
    parser.add_argument('data', help='test bytes sequence (python sequence)')
    parser.add_argument(
        '-i', '--init-timeout', type=float, default=1.0,
        help='time in seconds to wait after initialization (default: 1.0)'
    )
    parser.add_argument(
        '-r', '--response-timeout', type=float, default=3.0,
        help='time in seconds to wait for responses (default: 3.0)'
    )
    return parser.parse_args()


def run():
    args = parse_cli_args()

    rx_q = Queue()
    b42 = B42Handler(rx_frame_q=rx_q, port=args.port)
    sleep(args.init_timeout)  # some boards reset when connecting, give them time to get ready

    tx_frame = eval(args.data)
    print('sending frame: %s' % str(tx_frame))
    b42.send_frame(*tx_frame)

    while True:
        try:
            rx_frame = rx_q.get(True, args.response_timeout)
            print('received frame: %s' % str(rx_frame))
        except Empty:
            exit(0)
        except KeyboardInterrupt:
            exit(0)


if __name__ == '__main__':
    run()
