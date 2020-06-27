# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Helper classes and functions."""

import string


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
