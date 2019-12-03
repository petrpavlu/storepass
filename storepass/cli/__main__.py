# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import storepass.exc
import storepass.model
import storepass.storage
from storepass.cli import view

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

# Create a custom stderr logger. It is same as a handler that would be created
# by the logging module by default, but references sys.stderr at the time when a
# message is printed, which allows sys.stderr to be correctly overwritten in
# unit tests.
class StderrHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        print(log_entry, file=sys.stderr)
log_handler = StderrHandler()

# Initialize logging.
logging.basicConfig(
    format="%(app)s: %(levelname)s: %(message)s", handlers=[log_handler])
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def split_entry(entry):
    """
    Split a name of a password entry and return a list of its path elements.
    Character '/' is expected as the path separator and '\' starts an escape
    sequence.
    """

    STATE_NORMAL = 0
    STATE_ESCAPE = 1

    res = []
    state = STATE_NORMAL
    element = ""
    for c in entry:
        if state == STATE_NORMAL:
            if c == '/':
                res.append(element)
                element = ""
            elif c == '\\':
                state = STATE_ESCAPE
            else:
                element += c
        else:
            assert state == STATE_ESCAPE
            element += c
            state = STATE_NORMAL
    res.append(element)

    if state == STATE_ESCAPE:
        logger.warning(
            f"entry name '{entry}' has an incomplete escape sequence at its "
            f"end")

    return res

def process_init_command(args, model):
    """
    Handle the init command which is used to create an empty password database.
    """

    assert args.command == 'init'

    # Keep the model empty and let the main() function write out the database.
    return 0

def process_list_command(args, model):
    """
    Handle the list command which is used to print short information about all
    stored password entries.
    """

    assert args.command == 'list'

    plain_view = view.ListView()
    model.visit_all(plain_view)
    return 0

def process_show_command(args, model):
    """
    Handle the show command which is used to print detailed information about a
    single password entry.
    """

    assert args.command == 'show'
    assert len(args.entry) == 1

    # Find the entry specified on the command line.
    entry_name = args.entry[0]
    path = split_entry(entry_name)
    entry = model.get_entry(path)
    if entry is None:
        logger.error(f"entry '{entry_name}' not found")
        return 1

    detail_view = view.DetailView()
    entry.visit(detail_view, None)

def process_add_command(args, model):
    assert args.command == 'add'
    assert 0 and "Unimplemented command 'add'!"

def process_delete_command(args, model):
    assert args.command == 'delete'
    assert 0 and "Unimplemented command 'delete'!"

def process_edit_command(args, model):
    assert args.command == 'edit'
    assert 0 and "Unimplemented command 'edit'!"

def process_dump_command(args, storage):
    """
    Handle the dump command which is used to print the raw XML content of a
    password database.
    """

    assert args.command == 'dump'

    # Load the database content.
    try:
        plain_data = storage.read_plain()
    except storepass.exc.StorageReadException as e:
        logger.error(f"failed to load password database '{args.file}': {e}")
        return 1

    # Print the content.
    end = "" if len(plain_data) > 0 and plain_data[-1] == "\n" else "\n"
    print(plain_data, end=end)

    return 0

def main():
    """
    Main entry function. Returns 0 if the operation was successful and a
    non-zero value otherwise.
    """

    # Parse the command-line arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f', '--file', metavar='PASSDB',
        default=os.path.join(os.path.expanduser('~'), '.storepass.db'),
        help="password database file (the default is ~/.storepass.db)")
    parser.add_argument(
        '-v', '--verbose', action='count', help="increase verbosity level")

    # Add sub-commands.
    subparsers = parser.add_subparsers(dest='command')
    init_parser = subparsers.add_parser('init',
         description="create a new empty database")
    list_parser = subparsers.add_parser(
        'list', description="list password entries")
    show_parser = subparsers.add_parser(
        'show', description="show a password entry and its details")
    # TODO Share the option with other commands.
    show_parser.add_argument(
        'entry', nargs=1, metavar='ENTRY', help="password entry")
    add_parser = subparsers.add_parser(
        'add', description="add a new password entry")
    remove_parser = subparsers.add_parser(
        'delete', description="delete a password entry")
    edit_parser = subparsers.add_parser(
        'edit', description="edit an existing password entry")
    dump_parser = subparsers.add_parser(
        'dump', description="dump raw database content")

    try:
        args = parser.parse_args()
    except SystemExit as e:
        return e.code

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

    # Create a storage object.
    storage = storepass.storage.Storage(args.file, getpass.getpass)

    # Handle the dump command early because it does not require any high-level
    # representation.
    if args.command == 'dump':
        return process_dump_command(args, storage)

    # Create a data representation object.
    model = storepass.model.Model()

    try:
        model.load(storage)
    except storepass.exc.StorageReadException as e:
        logger.error(f"failed to load password database '{args.file}': {e}")
        return 1

    # Handle individual commands.
    if args.command == 'init':
        res = process_init_command(args, model)
    elif args.command == 'list':
        res = process_list_command(args, model)
    elif args.command == 'show':
        return process_show_command(args, model)
    elif args.command == 'add':
        return process_add_command(args, model)
    elif args.command == 'delete':
        return process_delete_command(args, model)
    elif args.command == 'edit':
        return process_edit_command(args, model)
    else:
        assert 0 and "Unimplemented command!"

    return 0

if __name__ == '__main__':
    sys.exit(main())
