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


class ErrorHandler(Queue):
    """Convenience error handler for :class:`B42Handler` and :class:`CommandHandler`.

    Intended for use as `rx_error_q` argument of the :class:`B42Handler` and
    :class:`CommandHandler` constructors.
    A provided callback is invoked for each queued :class:`B42Error`/:class:`CommandError`.
    The callback can be triggered synchronously or asynchronously.
    """

    def __init__(self, callback, async_process=False, **kwargs):
        """Initialize the error handler.

        :param callback: callable to call for queued errors
        :param async_process: if True, call the `callback` as soon as an error is
            queued (probably in the :class:`B42Handler` receiver thread context),
            else collect all errors and synchronously call the `callback` for each
            of them on a call to :method:`process_errors()`
        :param kwargs: passed to the :class:`Queue` parent constructor
        :raises: :class:`TypeError` if `callback` is not a callable
        """

        if not callable(callback):
            raise TypeError('callback is not a callable')
        super().__init__(**kwargs)
        self._callback = callback
        self._async_process = bool(async_process)

    def process_errors(self):
        """Synchronously trigger the callback.

        Call the callback for each queued error since the last call to
        :method:`process_errors()`.
        Has no effect when initialized for asynchronous processing.
        """

        while not self.empty():
            self._callback(self.get())

    def put(self, item, *_, **__):
        """Internal. Used by :class:`B42Handler` and :class:`CommandHandler`."""
        if self._async_process:
            self._callback(item)
        else:
            super().put(item)
