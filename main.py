#!/usr/bin/env python3

# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import storepass.model
import storepass.plainview
import storepass.storage

import argparse
import getpass
import logging
import os
import sys
import time

# Allow to specify application name in the log format.
old_factory = logging.getLogRecordFactory()
def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.app = os.path.basename(sys.argv[0])
    return record
logging.setLogRecordFactory(record_factory)

# Make level names lowercase.
logging.addLevelName(logging.CRITICAL, "critical")
logging.addLevelName(logging.ERROR, "error")
logging.addLevelName(logging.WARNING, "warning")
logging.addLevelName(logging.INFO, "info")
logging.addLevelName(logging.DEBUG, "debug")

# Initialize logging.
logging.basicConfig(format="%(app)s: %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def main():
    """Main entry function."""

    # Parse the command-line arguments.
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=None)
    parser.add_argument(
        '-f', '--file', metavar='PASSDB',
        default=os.path.join(os.path.expanduser('~'), '.storepass.db'),
        help="password database file (the default is ~/.storepass.db)")
    parser.add_argument(
        '-v', '--verbose', action='count', help="increase verbosity level")

    # Add sub-commands.
    subparsers = parser.add_subparsers(dest='command')
    add_parser = subparsers.add_parser(
        'add', description="add a new password entry")
    remove_parser = subparsers.add_parser(
        'remove', description="remove a password entry")
    edit_parser = subparsers.add_parser(
        'edit', description="edit an existing password entry")
    list_parser = subparsers.add_parser(
        'list', description="list password entries")
    dump_parser = subparsers.add_parser(
        'dump', description="dump raw database content")

    args = parser.parse_args()

    # Set desired log verbosity.
    if args.verbose is not None:
        assert args.verbose > 0
        level = ('INFO', 'DEBUG')[min(args.verbose, 2) - 1]
        logger.setLevel(level)
        logger.info(f"log verbosity set to '{level}'")

    # Handle the specified command.
    if args.command is None:
        parser.error("no command specified")
        return 1

    logger.debug(f"processing command '{args.command}' on file '{args.file}'")

    # Load the password database.
    if args.command == 'dump':
        reader_class = storepass.storage.PlainReader
    else:
        reader_class = storepass.storage.TreeReader

    try:
        storage = reader_class(args.file, getpass.getpass)
    except storepass.storage.ReadException as e:
        logger.error(f"failed to load password database '{args.file}': {e}")
        return 1

    # Handle the dump command which does not require any high-level
    # representation.
    if args.command == 'dump':
        print(storage.data, end="")
        return 0

    # Create data representation.
    model = storepass.model.Model()

    # TODO Error handling.
    model.load(storage)

    if args.command == 'list':
        view = storepass.plainview.PlainView()
        model.visit_all(view)
    else:
        # TODO Implement.
        assert 0 and "Unimplemented command!"

    return 0

if __name__ == '__main__':
    sys.exit(main())
