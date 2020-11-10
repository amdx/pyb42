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

from queue import Queue
from collections import namedtuple

from pyb42.b42handler import B42Frame

import logging
logger = logging.getLogger(__name__)

CMD_ERROR_UNREGISTERED = 0x0F  # unregistered command received
CMD_ERROR_NUM_DATA = 0x0E  # invalid number of data bytes received

CommandError = namedtuple('CommandError', 'timestamp code message')


class CommandHandler(Queue):
    """Handler/dispatcher for B42 commands (frames) received via :class:`B42Handler`.

    Intended for use as `rx_frame_q` argument of the :class:`B42Handler` constructor.
    Callbacks registered by :method:`register_command()` are dispatched for matching
    command codes. Dispatching can be triggered synchronously or asynchronously.
    """

    def __init__(self, rx_error_q=None, async_dispatch=False, **kwargs):
        """Initialize the command handler.

        :param rx_error_q: (optional) queue/handler to collect/dispatch B42 command
            errors (:class:`CommandError`), this can be a simple :class:`Queue` or a more
            convenient :class:`ErrorHandler`
        :param async_dispatch: if `True`, dispatch commands as soon as they arrive (in the
            :class:`B42Handler` receiver thread's context), else collect and synchronously
            dispatch them on a call to :method:`dispatch_commands()`
        :param kwargs: passed to the :class:`Queue` parent constructor
        """

        super().__init__(**kwargs)
        self._rx_error_q = rx_error_q
        self._async_dispatch = bool(async_dispatch)
        self._command_table = {}

    def register_command(self, code, callback, num_data=None):
        """Register a command callback for a command code.

        Callbacks are invoked with the `timestamp` and `data` fields of the
        received :class:`B42Frame`.

        :param code: B42 command code to register a callback for; if a callback
            for this `code` is already registered, it is replaced by the new one
        :param callback: callable to dispatch for `code`
        :param num_data: (optional) number of expected data bytes for the B42 command;
            if provided, the number of received command data bytes is checked before
            dispatching the command; can be :class:`int`, :class:`tuple` or :class:`list`
        :raises: :class:`TypeError` for invalid `code`, `callback` and `num_data` types
        """

        if type(code) is not int:
            raise TypeError('code <%s> is not an integer' % str(code))
        if not callable(callback):
            raise TypeError('callback is not a callable')
        if num_data is not None:
            if type(num_data) is int:
                num_data = (num_data,)
            elif type(num_data) in (tuple, list):
                for n in num_data:
                    if type(n) is not int:
                        raise TypeError('num_data contains non-integer value <%s>' % str(n))
            else:
                raise TypeError('num_data is not an integer or a tuple/list')

        if code in self._command_table:
            logger.warning('replacing registered command: <0x%02X>' % code)
        self._command_table[code] = (callback, num_data)

    def dispatch_commands(self):
        """Synchronously dispatch all received commands.

        Do (optional) number-of-data-bytes checks and call the registered callable for
        all B42 commands received since the last call to :method:`dispatch_commands()`.
        Has no effect when initialized for asynchronous dispatching.
        """

        while not self.empty():
            self._dispatch_command(self.get())

    def _dispatch_command(self, frame):
        assert frame.data is None or type(frame.data) is tuple
        command_info = self._command_table.get(frame.command, None)
        if command_info:
            callback, num_data = command_info
            if num_data is not None:  # check allowed number of data bytes
                len_data = len(frame.data) if frame.data else 0
                if len_data not in num_data:
                    self._process_error(
                        frame.timestamp, CMD_ERROR_NUM_DATA,
                        'invalid number of data bytes for command <0x%02X>: %d'
                        % (frame.command, len_data)
                    )
                    return
            callback(frame.timestamp, frame.data)
        else:
            self._process_error(
                frame.timestamp, CMD_ERROR_UNREGISTERED,
                'unregistered command received: <0x%02X>' % frame.command
            )

    def put(self, item, *_, **__):
        """Internal. Used by :class:`B42Handler`."""
        assert type(item) is B42Frame
        if self._async_dispatch:
            self._dispatch_command(item)
        else:
            super().put(item)

    def _process_error(self, timestamp, code, msg):
        if self._rx_error_q:
            self._rx_error_q.put(CommandError(timestamp, code, msg))
        logger.error('CMD [%.3f][0x%02X] %s', timestamp, code, msg)
