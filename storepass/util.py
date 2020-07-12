# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Helper classes and functions."""

import datetime
import string


class classproperty:
    """Limited read-only class property."""
    def __init__(self, fget):
        self._fget = fget

    def __get__(self, instance, owner=None):
        return self._fget(owner)

    def __set__(self, instance, value):
        raise AttributeError("can't set attribute")

    def __delete__(self, instance):
        raise AttributeError("can't delete attribute")


def escape_bytes(bytes_):
    """
    Convert a bytes object to an escaped string.

    Convert bytes to an ASCII string. Non-printable characters and a single
    quote (') are escaped. This allows to format bytes in messages as
    f"b'{util.escape_bytes(bytes)}'".
    """
    res = ""
    for byte in bytes_:
        char = chr(byte)
        if char == '\\':
            res += "\\\\"
        elif char == '\'':
            res += "\\'"
        elif char in (string.digits + string.ascii_letters +
                      string.punctuation + ' '):
            res += char
        else:
            res += "\\x%0.2x" % byte
    return res


def normalize_empty_to_none(text):
    """Return verbatim a given string if it is not empty or None otherwise."""
    return text if text != "" else None


def normalize_none_to_empty(text):
    """Return verbatim a given text or an empty string if the value is None."""
    return text if text is not None else ""


def get_current_datetime():
    """Obtain the current date+time in the UTC timezone."""
    return datetime.datetime.now(datetime.timezone.utc)
