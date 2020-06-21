# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""StorePass exceptions."""


class StorePassException(Exception):
    """Base StorePass exception."""


class ModelException(StorePassException):
    """Exception when working with a model."""


class StorageException(StorePassException):
    """Base storage exception."""


class StorageReadException(StorageException):
    """Error reading a password database."""


class StorageWriteException(StorageException):
    """Error writing a password database."""
