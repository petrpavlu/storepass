# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""StorePass command line interface."""

import argparse
import datetime
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
# by the logging module by default, but references sys.stderr at the time when
# a message is printed, which allows sys.stderr to be correctly overwritten in
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


def _get_entry_password():
    """Obtain an entry's password from the user."""
    password = getpass.getpass("Entry password: ")
    if password != '':
        return password
    return None


def _process_init_command(args, _model):
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
    try:
        path_spec = storepass.model.path_string_to_spec(entry_name)
        entry = model.get_entry(path_spec)
    except storepass.exc.ModelException as e:
        _logger.error("%s", e)
        return 1

    detail_view = view.DetailView()
    entry.accept(detail_view, single=True)
    return 0


def _validate_add_command(args):
    """Validate command-line options for the add command."""
    # Check that property arguments are valid for a given type.
    return _check_property_arguments(args, args.type)


def _process_add_command(args, model):
    """
    Handle the add command which is used to insert a new single password entry.
    """

    assert args.command == 'add'

    # Create the entry specified on the command line.
    entry_name = args.entry[0]
    try:
        path_spec = storepass.model.path_string_to_spec(entry_name)
    except storepass.exc.ModelException as e:
        _logger.error("%s", e)
        return 1

    if args.password:
        password = _get_entry_password()
    else:
        password = None

    updated = datetime.datetime.now(datetime.timezone.utc)

    if args.type == 'folder':
        entry = storepass.model.Folder(path_spec[-1], args.description,
                                       updated, args.notes, [])
    elif args.type == 'credit-card':
        entry = storepass.model.CreditCard(path_spec[-1], args.description,
                                           updated, args.notes, args.card_type,
                                           args.card_number, args.expiry_date,
                                           args.ccv, args.pin)
    elif args.type == 'crypto-key':
        entry = storepass.model.CryptoKey(path_spec[-1], args.description,
                                          updated, args.notes, args.hostname,
                                          args.certificate, args.keyfile,
                                          password)
    elif args.type == 'database':
        entry = storepass.model.Database(path_spec[-1], args.description,
                                         updated, args.notes, args.hostname,
                                         args.username, password,
                                         args.database)
    elif args.type == 'door':
        entry = storepass.model.Door(path_spec[-1], args.description, updated,
                                     args.notes, args.location, args.code)
    elif args.type == 'email':
        entry = storepass.model.Email(path_spec[-1], args.description, updated,
                                      args.notes, args.email, args.hostname,
                                      args.username, password)
    elif args.type == 'ftp':
        entry = storepass.model.FTP(path_spec[-1], args.description, updated,
                                    args.notes, args.hostname, args.port,
                                    args.username, password)
    elif args.type == 'generic':
        entry = storepass.model.Generic(path_spec[-1], args.description,
                                        updated, args.notes, args.hostname,
                                        args.username, password)
    elif args.type == 'phone':
        entry = storepass.model.Phone(path_spec[-1], args.description, updated,
                                      args.notes, args.phone_number, args.pin)
    elif args.type == 'shell':
        entry = storepass.model.Shell(path_spec[-1], args.description, updated,
                                      args.notes, args.hostname, args.domain,
                                      args.username, password)
    elif args.type == 'remote-desktop':
        entry = storepass.model.RemoteDesktop(path_spec[-1], args.description,
                                              updated, args.notes,
                                              args.hostname, args.port,
                                              args.username, password)
    elif args.type == 'vnc':
        entry = storepass.model.VNC(path_spec[-1], args.description, updated,
                                    args.notes, args.hostname, args.port,
                                    args.username, password)
    elif args.type == 'website':
        entry = storepass.model.Website(path_spec[-1], args.description,
                                        updated, args.notes, args.url,
                                        args.username, args.email, password)
    else:
        assert 0 and "Unhandled entry type!"

    # Insert the new entry in the model.
    try:
        parent_entry = model.get_entry(path_spec[:-1])
        model.add_entry(entry, parent_entry)
    except storepass.exc.ModelException as e:
        _logger.error("%s", e)
        return 1
    return 0


def _process_edit_command(args, model):
    """Handle the edit command which is used to modify an existing entry."""
    assert args.command == 'edit'
    assert len(args.entry) == 1

    # Find the entry specified on the command line.
    entry_name = args.entry[0]
    try:
        path_spec = storepass.model.path_string_to_spec(entry_name)
        entry = model.get_entry(path_spec)
    except storepass.exc.ModelException as e:
        _logger.error("%s", e)
        return 1

    # Check that property arguments are valid for a given type.
    type_map = {
        storepass.model.Folder: 'folder',
        storepass.model.CreditCard: 'credit-card',
        storepass.model.CryptoKey: 'crypto-key',
        storepass.model.Database: 'database',
        storepass.model.Door: 'door',
        storepass.model.Email: 'email',
        storepass.model.FTP: 'ftp',
        storepass.model.Generic: 'generic',
        storepass.model.Phone: 'phone',
        storepass.model.Shell: 'shell',
        storepass.model.RemoteDesktop: 'remote-desktop',
        storepass.model.VNC: 'vnc',
        storepass.model.Website: 'website',
    }
    assert type(entry) in type_map and "Unhandled entry type!"
    res = _check_property_arguments(args, type_map[type(entry)])
    if res != 0:
        return res

    # Process options valid for all entries.
    if args.description is not None:
        entry.description = args.description
    if args.notes is not None:
        entry.notes = args.notes

    # Process password entry-specific options.
    if args.card_number is not None:
        entry.card_number = args.card_number
    if args.card_type is not None:
        entry.card_type = args.card_type
    if args.ccv is not None:
        entry.ccv = args.ccv
    if args.certificate is not None:
        entry.certificate = args.certificate
    if args.code is not None:
        entry.code = args.code
    if args.database is not None:
        entry.database = args.database
    if args.domain is not None:
        entry.domain = args.domain
    if args.email is not None:
        entry.email = args.email
    if args.expiry_date is not None:
        entry.expiry_date = args.expiry_date
    if args.hostname is not None:
        entry.hostname = args.hostname
    if args.keyfile is not None:
        entry.keyfile = args.keyfile
    if args.location is not None:
        entry.location = args.location
    if args.password:
        entry.password = _get_entry_password()
    if args.phone_number is not None:
        entry.phone_number = args.phone_number
    if args.pin is not None:
        entry.pin = args.pin
    if args.port is not None:
        entry.port = args.port
    if args.url is not None:
        entry.url = args.url
    if args.username is not None:
        entry.username = args.username

    # Bump the updated date.
    entry.updated = datetime.datetime.now(datetime.timezone.utc)

    return 0


def _process_delete_command(args, model):
    """
    Handle the delete command which is used to wipe a single password entry.
    """

    assert args.command == 'delete'
    assert len(args.entry) == 1

    # Delete the entry specified on the command line.
    entry_name = args.entry[0]
    try:
        path_spec = storepass.model.path_string_to_spec(entry_name)
        entry = model.get_entry(path_spec)
        model.remove_entry(entry)
    except storepass.exc.ModelException as e:
        _logger.error("%s", e)
        return 1

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
        _logger.error("failed to load password database '%s': %s", args.file,
                      e)
        return 1

    # Print the content.
    end = "" if len(plain_data) > 0 and plain_data[-1] == "\n" else "\n"
    print(plain_data, end=end)

    return 0


ACCOUNT_ARGUMENT_VALIDITY = {
    'credit-card': ['card-type', 'card-number', 'expiry-date', 'ccv', 'pin'],
    'crypto-key': ['hostname', 'certificate', 'keyfile', 'password'],
    'database': ['hostname', 'username', 'password', 'database'],
    'door': ['location', 'code'],
    'email': ['email', 'hostname', 'username', 'password'],
    'ftp': ['hostname', 'port', 'username', 'password'],
    'generic': ['hostname', 'username', 'password'],
    'phone': ['phone-number', 'pin'],
    'shell': ['hostname', 'domain', 'username', 'password'],
    'remote-desktop': ['hostname', 'port', 'username', 'password'],
    'vnc': ['hostname', 'port', 'username', 'password'],
    'website': ['url', 'username', 'email', 'password']
}


def _check_property_arguments(args, type_):
    """
    Check validity of specified property arguments for a given entry type.

    Check that all type-related options specified on the command line are valid
    for a given entry type. An error is logged if some option is not available.
    Returns 0 if the check was successful, or 1 on failure.
    """
    assert args.command in ('add', 'edit')

    if type_ == 'folder':
        accepted_options = set()
    else:
        accepted_options = set(ACCOUNT_ARGUMENT_VALIDITY[type_])

    def _check_one(option, value):
        if value is not None and option not in accepted_options:
            _logger.error("option --%s is not valid for entry type '%s'",
                          option, type_)
            return 1
        return 0

    invalid = 0
    invalid += _check_one('card-number', args.card_number)
    invalid += _check_one('card-type', args.card_type)
    invalid += _check_one('ccv', args.ccv)
    invalid += _check_one('certificate', args.certificate)
    invalid += _check_one('code', args.code)
    invalid += _check_one('database', args.database)
    invalid += _check_one('domain', args.domain)
    invalid += _check_one('email', args.email)
    invalid += _check_one('expiry-date', args.expiry_date)
    invalid += _check_one('hostname', args.hostname)
    invalid += _check_one('keyfile', args.keyfile)
    invalid += _check_one('location', args.location)
    invalid += _check_one('password', args.password)
    invalid += _check_one('phone-number', args.phone_number)
    invalid += _check_one('pin', args.pin)
    invalid += _check_one('port', args.port)
    invalid += _check_one('url', args.url)
    invalid += _check_one('username', args.username)
    return 1 if invalid > 0 else 0


def _add_property_arguments(parser):
    """Add all command-line arguments to set entry properties."""
    common_group = parser.add_argument_group(
        "optional arguments valid for all entry types")
    common_group.add_argument(
        '--description',
        metavar='DESC',
        help="set entry description to the specified value")
    common_group.add_argument('--notes',
                              help="set entry notes to the specified value")

    account_group = parser.add_argument_group(
        "optional arguments valid for specific account types")
    account_group.add_argument('--card-number',
                               metavar='ID',
                               help="set card number to the specified value")
    account_group.add_argument('--card-type',
                               metavar='TYPE',
                               help="set card type to the specified value")
    account_group.add_argument('--ccv',
                               metavar='CCV',
                               help="set CCV number to the specified value")
    account_group.add_argument('--certificate',
                               metavar='CERT',
                               help="set certificate to the specified value")
    account_group.add_argument('--code',
                               metavar='CODE',
                               help="set code to the specified value")
    account_group.add_argument('--database',
                               metavar='NAME',
                               help="set database name to the specified value")
    account_group.add_argument('--domain',
                               metavar='NAME',
                               help="set domain name to the specified value")
    account_group.add_argument('--email',
                               metavar='ADDRESS',
                               help="set email to the specified value")
    account_group.add_argument('--expiry-date',
                               metavar='DATE',
                               help="set expiry date to the specified value")
    account_group.add_argument('--hostname',
                               metavar='HOST',
                               help="set hostname to the specified value")
    account_group.add_argument('--keyfile',
                               metavar='FILE',
                               help="set keyfile to the specified value")
    account_group.add_argument('--location',
                               metavar='PLACE',
                               help="set location to the specified value")
    account_group.add_argument('--password',
                               action='store_true',
                               default=None,
                               help="prompt for a password value")
    account_group.add_argument('--phone-number',
                               metavar='PHONE',
                               help="set phone number to the specified value")
    account_group.add_argument('--pin',
                               metavar='PIN',
                               help="set PIN to the specified value")
    account_group.add_argument('--port',
                               metavar='NUMBER',
                               help="set port to the specified value")
    account_group.add_argument('--url',
                               metavar='ADDRESS',
                               help="set URL to the specified value")
    account_group.add_argument('--username',
                               metavar='USER',
                               help="set username to the specified value")


def _build_parser():
    """Create and initialize a command-line parser."""
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
    _init_parser = subparsers.add_parser(
        'init', description="create a new empty database")
    _list_parser = subparsers.add_parser('list',
                                         description="list password entries")
    show_parser = subparsers.add_parser(
        'show', description="show a password entry and its details")
    add_edit_epilog = "option validity for account types:\n" + "\n".join([
        f"  {type_ + ':':22}{', '.join(args)}"
        for type_, args in ACCOUNT_ARGUMENT_VALIDITY.items()
    ])
    add_parser = subparsers.add_parser(
        'add',
        description="add a new password entry",
        epilog=add_edit_epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    edit_parser = subparsers.add_parser(
        'edit',
        description="edit an existing password entry",
        epilog=add_edit_epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    delete_parser = subparsers.add_parser(
        'delete', description="delete a password entry")
    _dump_parser = subparsers.add_parser(
        'dump', description="dump raw database content")

    add_parser.add_argument('--type',
                            choices=('folder', 'credit-card', 'crypto-key',
                                     'database', 'door', 'email', 'ftp',
                                     'generic', 'phone', 'shell',
                                     'remote-desktop', 'vnc', 'website'),
                            default='generic',
                            help="entry type (the default is generic)")

    for sub_parser in (add_parser, edit_parser):
        _add_property_arguments(sub_parser)

    for sub_parser in (show_parser, add_parser, delete_parser, edit_parser):
        sub_parser.add_argument('entry',
                                nargs=1,
                                metavar='ENTRY',
                                help="password entry")

    return parser


def main():
    """
    Main entry function. Returns 0 if the operation was successful and a
    non-zero value otherwise.
    """

    # Parse the command-line arguments.
    parser = _build_parser()
    try:
        args = parser.parse_args()
    except SystemExit as e:
        return e.code

    # Do further command-specific checks of the command line options.
    if args.command == 'add':
        res = _validate_add_command(args)
    else:
        # No extra checks needed.
        res = 0

    # Bail out if the checks failed.
    if res != 0:
        return res

    # Set desired log verbosity.
    if args.verbose is not None:
        assert args.verbose > 0
        level = ('INFO', 'DEBUG')[min(args.verbose, 2) - 1]
        _logger.setLevel(level)
        _logger.info("log verbosity set to '%s'", level)

    # Handle the specified command.
    if args.command is None:
        parser.error("no command specified")
        return 1

    _logger.debug("processing command '%s' on file '%s'", args.command,
                  args.file)

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
            _logger.error("failed to load password database '%s': %s",
                          args.file, e)
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
        try:
            exclusive = args.command == 'init'
            model.save(storage, exclusive)
        except storepass.exc.StorageWriteException as e:
            _logger.error("failed to save password database '%s': %s",
                          args.file, e)
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
