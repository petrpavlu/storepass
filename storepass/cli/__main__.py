# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import argparse
import getpass
import logging
import os
import sys

import storepass.exc
import storepass.model
import storepass.storage
from storepass.cli import view


# Allow to specify application name in the log format.
def _record_factory(*args, **kwargs):
    record = _old_factory(*args, **kwargs)
    record.app = os.path.basename(sys.argv[0])
    return record


_old_factory = logging.getLogRecordFactory()
logging.setLogRecordFactory(_record_factory)

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
class _StderrHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        print(log_entry, file=sys.stderr)


_log_handler = _StderrHandler()

# Initialize logging.
logging.basicConfig(format="%(app)s: %(levelname)s: %(message)s",
                    handlers=[_log_handler])
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)


def _split_entry(entry):
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
        _logger.warning(
            f"entry name '{entry}' has an incomplete escape sequence at its "
            f"end")

    return res


def _process_init_command(args, model):
    """
    Handle the init command which is used to create an empty password database.
    """

    assert args.command == 'init'

    # Keep the model empty and let the main() function write out the database.
    return 0


def _process_list_command(args, model):
    """
    Handle the list command which is used to print short information about all
    stored password entries.
    """

    assert args.command == 'list'

    plain_view = view.ListView()
    model.visit_all(plain_view)
    return 0


def _process_show_command(args, model):
    """
    Handle the show command which is used to print detailed information about a
    single password entry.
    """

    assert args.command == 'show'
    assert len(args.entry) == 1

    # Find the entry specified on the command line.
    entry_name = args.entry[0]
    path = _split_entry(entry_name)
    entry = model.get_entry(path)
    if entry is None:
        _logger.error(f"entry '{entry_name}' not found")
        return 1

    detail_view = view.DetailView()
    entry.visit(detail_view, None)
    return 0


def _check_options_validity(type_, accepted_options, args):
    all_valid = True

    if args.hostname is not None and 'hostname' not in accepted_options:
        _logger.error(
            f"option --hostname is not valid for entry type '{type_}'")
        all_valid = False
    if args.username is not None and 'username' not in accepted_options:
        _logger.error(
            f"option --username is not valid for entry type '{type_}'")
        all_valid = False
    if args.password is not None and 'password' not in accepted_options:
        _logger.error(
            f"option --password is not valid for entry type '{type_}'")
        all_valid = False

    return all_valid


def _process_add_command(args, model):
    assert args.command == 'add'

    # Create the entry specified on the command line.
    entry_name = args.entry[0]
    path = _split_entry(entry_name)

    if args.password:
        # TODO Implement, prompt for a password.
        password = 'TODO'
    else:
        password = None

    if args.type == 'generic':
        if not _check_options_validity(
                'generic', ('hostname', 'username', 'password'), args):
            return 1

        # TODO Pass proper updated value.
        entry = storepass.model.Generic(path[-1], args.description, None,
                                        args.notes, args.hostname,
                                        args.username, password)

    elif args.type == 'folder':
        if not _check_options_validity('folder', (), args):
            return 1

        # TODO Pass proper updated value.
        entry = storepass.model.Folder(path[-1], args.description, None,
                                       args.notes)

    else:
        assert 0 and "Unhandled entry type!"

    # TODO Implement error handling.
    model.add_entry(path[:-1], entry)
    return 0


def _process_edit_command(args, model):
    assert args.command == 'edit'
    assert len(args.entry) == 1

    # Find the entry specified on the command line.
    entry_name = args.entry[0]
    path = _split_entry(entry_name)
    entry = model.get_entry(path)
    if entry is None:
        _logger.error(f"entry '{entry_name}' not found")
        return 1

    # Process options valid for all entries.
    if args.description is not None:
        entry.description = args.description
    if args.notes is not None:
        entry.notes = args.notes

    # Process password entry-specific options.
    has_error = False
    if args.username is not None:
        if isinstance(entry, storepass.model.Generic):
            entry.username = args.username
        else:
            _logger.error(f"TODO")
            has_error = True
    if args.hostname is not None:
        if isinstance(entry, storepass.model.Generic):
            entry.hostname = args.hostname
        else:
            _logger.error(f"TODO")
            has_error = True
    if args.password:
        if isinstance(entry, storepass.model.Generic):
            entry.password = getpass.getpass("Entry password: ")
        else:
            _logger.error(f"TODO")
            has_error = True
    if has_error:
        return 1

    return 0


def _process_delete_command(args, model):
    assert args.command == 'delete'
    assert 0 and "Unimplemented command 'delete'!"

    return 0

def _process_dump_command(args, storage):
    """
    Handle the dump command which is used to print the raw XML content of a
    password database.
    """

    assert args.command == 'dump'

    # Load the database content.
    try:
        plain_data = storage.read_plain()
    except storepass.exc.StorageReadException as e:
        _logger.error(f"failed to load password database '{args.file}': {e}")
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
        '-f',
        '--file',
        metavar='PASSDB',
        default=os.path.join(os.path.expanduser('~'), '.storepass.db'),
        help="password database file (the default is ~/.storepass.db)")
    parser.add_argument('-v',
                        '--verbose',
                        action='count',
                        help="increase verbosity level")

    # Add sub-commands.
    subparsers = parser.add_subparsers(dest='command')
    init_parser = subparsers.add_parser(
        'init', description="create a new empty database")
    list_parser = subparsers.add_parser('list',
                                        description="list password entries")
    show_parser = subparsers.add_parser(
        'show', description="show a password entry and its details")
    add_parser = subparsers.add_parser('add',
                                       description="add a new password entry")
    edit_parser = subparsers.add_parser(
        'edit', description="edit an existing password entry")
    delete_parser = subparsers.add_parser(
        'delete', description="delete a password entry")
    dump_parser = subparsers.add_parser(
        'dump', description="dump raw database content")

    add_parser.add_argument('-t',
                            '--type',
                            choices=('folder', 'generic'),
                            default='generic',
                            help="entry type (the default is generic)")

    for sub_parser in (add_parser, edit_parser):
        common_group = sub_parser.add_argument_group(
            "optional arguments valid for all entry types")
        common_group.add_argument(
            '--description',
            metavar='DESC',
            help="set entry description to the specified value")
        common_group.add_argument(
            '--notes', help="set entry notes to the specified value")

        password_group = sub_parser.add_argument_group(
            "optional arguments valid for password type")
        password_group.add_argument('--hostname',
                                    metavar='HOST',
                                    help="set hostname to the specified value")
        password_group.add_argument('--username',
                                    metavar='USER',
                                    help="set username to the specified value")
        password_group.add_argument('--password',
                                    action='store_true',
                                    help="prompt for a password value")

    for sub_parser in (show_parser, add_parser, delete_parser, edit_parser):
        sub_parser.add_argument('entry',
                                nargs=1,
                                metavar='ENTRY',
                                help="password entry")

    try:
        args = parser.parse_args()
    except SystemExit as e:
        return e.code

    # Set desired log verbosity.
    if args.verbose is not None:
        assert args.verbose > 0
        level = ('INFO', 'DEBUG')[min(args.verbose, 2) - 1]
        _logger.setLevel(level)
        _logger.info(f"log verbosity set to '{level}'")

    # Handle the specified command.
    if args.command is None:
        parser.error("no command specified")
        return 1

    _logger.debug(f"processing command '{args.command}' on file '{args.file}'")

    # Create a password proxy that asks the user for the database password only
    # once.
    db_password = None
    def get_db_password():
        nonlocal db_password
        if db_password is None:
            db_password = getpass.getpass("Database password: ")
        return db_password

    # Create a storage object.
    storage = storepass.storage.Storage(args.file, get_db_password)

    # Handle the dump command early because it does not require any high-level
    # representation.
    if args.command == 'dump':
        return _process_dump_command(args, storage)

    # Create a data representation object.
    model = storepass.model.Model()

    if args.command in ('list', 'show', 'add', 'edit', 'delete'):
        try:
            model.load(storage)
        except storepass.exc.StorageReadException as e:
            _logger.error(
                f"failed to load password database '{args.file}': {e}")
            return 1

    # Handle individual commands.
    if args.command == 'init':
        res = _process_init_command(args, model)
    elif args.command == 'list':
        res = _process_list_command(args, model)
    elif args.command == 'show':
        res = _process_show_command(args, model)
    elif args.command == 'add':
        res = _process_add_command(args, model)
    elif args.command == 'edit':
        res = _process_edit_command(args, model)
    elif args.command == 'delete':
        res = _process_delete_command(args, model)
    else:
        assert 0 and "Unimplemented command!"

    # Bail out if the command failed.
    if res != 0:
        return res

    if args.command in ('init', 'add', 'edit', 'delete'):
        # TODO Error handling.
        model.save(storage)

    return 0


if __name__ == '__main__':
    sys.exit(main())
