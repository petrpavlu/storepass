# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT


class StorePassException(Exception):
    """Base StorePass exception."""


class StorageException(StorePassException):
    """Base Storage exception."""


class StorageReadException(StorageException):
    """Error reading a password database."""


class StorageWriteException(StorageException):
    """Error writing a password database."""
