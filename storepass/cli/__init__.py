# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Initialization of the CLI module."""

import logging
import os
import sys


# Create a custom stderr logger. It is same as a handler that would be created
# by the logging module by default but references sys.stderr at the time when a
# message is printed which allows sys.stderr to be correctly overwritten in
# unit tests.
class _StderrHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        print(log_entry, file=sys.stderr)


_log_handler = _StderrHandler()

# Initialize logging.
logging.basicConfig(format="%(levelname)s: %(name)s: %(message)s",
                    handlers=[_log_handler])
_logger = logging.getLogger()
