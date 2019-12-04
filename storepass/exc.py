# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT


class StorePassException(Exception):
    """Base StorePass exception."""
    pass


class StorageException(StorePassException):
    """Base Storage exception."""
    pass


class StorageReadException(StorageException):
    """Error reading a password database."""
    pass


class StorageWriteException(StorageException):
    """Error writing a password database."""
    pass
