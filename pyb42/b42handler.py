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

import threading
import time
from collections import namedtuple
import serial

import logging
logger = logging.getLogger(__name__)

# protocol errors
B42_ERROR_ZERO_BYTE = 0x01  # invalid 0x00 byte received
B42_ERROR_EXPECT_COMMAND = 0x02  # command byte expected (seq==0)
B42_ERROR_EXPECT_DATA1 = 0x03  # data byte 1 expected (seq==1)
B42_ERROR_EXPECT_DATA2 = 0x04  # data byte 2 expected (seq==2)
B42_ERROR_EXPECT_DATA3 = 0x05  # data byte 3 expected (seq==3)

B42Frame = namedtuple('B42Frame', 'timestamp command data')
B42Error = namedtuple('B42Error', 'timestamp code message')


class B42Handler(threading.Thread):
    """B42 protocol based serial communication handler.

    Send/receive B42 frames to/from a board connected via a serial port or socket.
    Sending is done synchronously. Receiving and byte/frame processing are executed
    in a thread, valid frames are passed to a queue.
    """

    DEFAULT_PORT = '/dev/ttyS0'
    DEFAULT_BAUD = 115200
    DEFAULT_SOCKET_PORT = 10001  # used by e.g. XPort

    _STATE_CMD0 = 0x00  # = command byte sequence bits
    _STATE_DATA1 = 0x40  # = data1 byte sequence bits
    _STATE_DATA2 = 0x80  # = data2 byte sequence bits
    _STATE_DATA3 = 0xC0  # = data3 byte sequence bits

    _MASK_SEQ = 0xC0
    _MASK_CMD = 0x0F
    _MASK_DATA = 0x3F

    _SHIFT_SEQNUM = 6  # bits 7:6
    _SHIFT_NUMBYTES = 4  # command byte bits 5:4

    @staticmethod
    def encode_value(value, length):
        """Convert a single int value into a sequence of 1 to 3 B42 data bytes.

        :param value: int value to convert (silently truncated to `length` * 6 bits)
        :param length: number of data bytes (1, 2 or 3)
        :returns: :class:`tuple` of `length` encoded B42 data bytes
        :raises: :class:`ValueError` for invalid data `length`
        """

        if length not in (1, 2, 3):
            raise ValueError('invalid data length <%s>' % str(length))

        b42_bytes = [0] * length
        b42_bytes[-1] = value & 0x3F
        if 1 < length:
            value >>= 6
            b42_bytes[-2] = value & 0x3F
            if 2 < length:
                value >>= 6
                b42_bytes[-3] = value & 0x3F
        return tuple(b42_bytes)

    @staticmethod
    def decode_value(*b42_bytes):
        """Convert a sequence of 1 to 3 B42 data bytes into a single int value.

        :param b42_bytes: 1 to 3 B42 data bytes to convert
        :returns: decoded int value
        :raises: :class:`ValueError` for invalid number of `b42_bytes`
        """

        length = len(b42_bytes)
        if length not in (1, 2, 3):
            raise ValueError('invalid number of data bytes <%d>' % length)

        value = b42_bytes[0]
        if 1 < length:
            value <<= 6
            value |= b42_bytes[1]
            if 2 < length:
                value <<= 6
                value |= b42_bytes[2]
        return value

    def __init__(self, rx_frame_q=None, rx_error_q=None, port=DEFAULT_PORT, baudrate=DEFAULT_BAUD, start=True):
        """Initialize the connection to the board.

        Establish the low level serial or socket connection to the remote board and
        start a receiver thread.

        :param rx_frame_q: (optional) queue/handler to collect/dispatch received
            :class:`B42Frame`s, this can be a simple :class:`Queue` or a more
            convenient :class:`CommandHandler`
        :param rx_error_q: (optional) queue/handler to collect/dispatch B42 protocol
            errors (:class:`B42Error`), this can be a simple :class:`Queue` or a more
            convenient :class:`ErrorHandler`
        :param port: serial port to connect to, format for network-serial-bridges is
            "socket://<host>[:<port-num>]"
        :param baudrate: serial baud rate
        :param start: if `True`, the receiver thread is started automatically, else
            :method:`start()` has to be called manually to begin receiving B42 frames
        :raises: :class:`serial.SerialException` if serial connection fails
        """

        super().__init__(daemon=True)
        self._rx_frame_q = rx_frame_q
        self._rx_error_q = rx_error_q

        port = B42Handler._check_socket_port(port)
        self._serial = serial.serial_for_url(port, baudrate=baudrate, timeout=0.5)

        self._running = False
        if start:
            self.start()

    @property
    def port(self):
        """The serial port connected to."""
        return self._serial.port

    @property
    def baudrate(self):
        """The serial baudrate used."""
        return self._serial.baudrate

    def stop(self):
        """Stop the serial receiver thread.

        The B42 handler doesn't receive frames anymore and the receiver thread can't
        be started again. To receive frames after a call to :method:`stop()`, the B42
        handler needs to be re-created and set up.
        """

        self._running = False
        self.join()
        self._serial.close()

    def reset(self, hard=True):
        """Reset the serial connection (flush buffers) and optionally reset the board as well.

        :param hard: if `True`, reset the board by toggling the serial DTR/RTS control lines
        """

        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()

        if hard:
            self._serial.dtr = 0
            self._serial.rts = 0
            time.sleep(0.1)
            self._serial.dtr = 1
            self._serial.rts = 1
            time.sleep(0.1)
            self._serial.dtr = 0
            self._serial.rts = 0

    def send_frame(self, command, *data):
        """Send a B42 frame.

        Synchronously send a B42 frame composed of `command` and optional `data` bytes
        to the board.

        :param command: the command byte for the B42 frame (range [0x01..0x0F])
        :param data: (optional) up to 3 data bytes payload for the B42 frame
            (range [0x00..0x3F] each)
        :returns: total number of bytes sent
        :raises: :class:`ValueError` for invalid `command` and `data` bytes
        """

        def send_byte(byte):
            return self._serial.write(bytes((byte,)))

#        print('TX:', hex(command), str(data))
        if command < 0x01 or 0x0F < command:
            raise ValueError('command <0x%02X> out of range [0x01..0x0F]' % command)
        if len(data):
            if 3 < len(data):
                raise ValueError('more than 3 data bytes: <%s>' % str(data))
            for i, d in enumerate(data):
                if d < 0x00 or 0x3F < d:
                    raise ValueError('data%d <0x%02X> out of range [0x00..0x3F]' % (i + 1, d))
        length = send_byte(command | (len(data) << B42Handler._SHIFT_NUMBYTES))
        if len(data):
            length += send_byte(data[0] | B42Handler._STATE_DATA1)
            if 1 < len(data):
                length += send_byte(data[1] | B42Handler._STATE_DATA2)
                if 2 < len(data):
                    length += send_byte(data[2] | B42Handler._STATE_DATA3)
        return length

    @staticmethod
    def _check_socket_port(port):
        if port.startswith('socket://'):
            split = port.split(':')
            if len(split) == 2:  # no socket port provided, set to default
                return '%s:%d' % (port, B42Handler.DEFAULT_SOCKET_PORT)
        return port

    # asynchronous part - receive and process incoming bytes/frames #

    def run(self):
        """Internal. The receiver thread loop."""
        state = B42Handler._STATE_CMD0
        timestamp = None
        command = None
        num_bytes = None
        data = [None] * 3

        self._running = True
        while self._running:
            # receive next byte
            rx_bytes = self._serial.read()
            if rx_bytes == b'':  # timeout
                continue
            rx_byte = rx_bytes[0]
#            print('rx:', hex(rx_byte))

            # check for valid byte
            if rx_byte == 0x00:  # ERROR: invalid 0x00 byte received
                self._process_error(B42_ERROR_ZERO_BYTE, '0x00 byte received')
                state = B42Handler._STATE_CMD0
                continue  # wait for next valid command byte
            seq_bits = rx_byte & B42Handler._MASK_SEQ  # rx sequence bits
            if seq_bits != state:  # ERROR: invalid rx sequence number
                if state == B42Handler._STATE_CMD0:
                    self._process_error(
                        B42_ERROR_EXPECT_COMMAND,
                        'expected command byte, received <0x%02X>' % rx_byte
                    )
                    continue  # wait for next valid command byte
                else:
                    exp_num = state >> B42Handler._SHIFT_SEQNUM
                    self._process_error(
                        B42_ERROR_EXPECT_DATA1 + exp_num - 1,
                        'expected data byte %d, received <0x%02X>' % (exp_num, rx_byte)
                    )
                    state = B42Handler._STATE_CMD0
                    if seq_bits != B42Handler._STATE_CMD0:  # not a command byte
                        continue  # wait for next valid command byte
                    # else: process this command byte

            # process received byte
            if state == B42Handler._STATE_CMD0:
                timestamp = time.time()
                command = rx_byte & B42Handler._MASK_CMD
                num_bytes = rx_byte >> B42Handler._SHIFT_NUMBYTES
                if num_bytes == 0:  # no data bytes, process frame
                    self._process_frame(timestamp, command, None)
                else:  # receive data byte 1
                    state = B42Handler._STATE_DATA1
            else:  # state == _STATE_DATAx
                assert num_bytes
                seq_num = state >> B42Handler._SHIFT_SEQNUM
                data[seq_num - 1] = rx_byte & B42Handler._MASK_DATA
                if seq_num == num_bytes:  # no more data bytes, process frame
                    self._process_frame(timestamp, command, data[:num_bytes])
                    state = B42Handler._STATE_CMD0  # receive next frame
                else:  # receive next data byte
                    state += B42Handler._STATE_DATA1  # next _STATE_DATAx
                    assert state <= B42Handler._STATE_DATA3

    def _process_frame(self, timestamp, command, data):
#        print('RX:', hex(command), str(data))
        if self._rx_frame_q:
            self._rx_frame_q.put(B42Frame(timestamp, command, tuple(data) if data else None))

    def _process_error(self, code, msg):
#        print('ERR:', code, msg)
        now = time.time()
        if self._rx_error_q:
            self._rx_error_q.put(B42Error(now, code, msg))
        logger.error('B42 [%.3f][0x%02X] %s', now, code, msg)
