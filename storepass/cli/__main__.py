# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""StorePass command line interface."""

import argparse
import getpass
import logging
import os
import sys

import storepass.exc
import storepass.model
import storepass.storage
import storepass.util
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


class _EntryGenerator:
    """Generator to create a new entry."""
    def __init__(self, name):
        """Initialize an entry generator."""
        self.type = None

        self.name = name
        self.description = None
        self.updated = None
        self.notes = None

        self.card_number = None
        self.card_type = None
        self.ccv = None
        self.certificate = None
        self.code = None
        self.database = None
        self.domain = None
        self.email = None
        self.expiry_date = None
        self.hostname = None
        self.keyfile = None
        self.location = None
        self.password = None
        self.phone_number = None
        self.pin = None
        self.port = None
        self.url = None
        self.username = None

    def set_from_entry(self, entry):
        """Update generator properties from an existing entry."""
        self.type = entry.entry_type_name

        self.description = entry.description
        self.updated = entry.updated
        self.notes = entry.notes

        entry.accept(self, single=True)

    def _normalize_argument(self, value):
        """Normalize an argument value to None if it is an empty string."""
        return storepass.util.normalize_empty_to_none(value)

    def set_from_args(self, args):
        """Update generator properties from command line arguments."""
        if args.type is not None:
            self.type = args.type

        # Process options valid for all entries.
        if args.description is not None:
            self.description = self._normalize_argument(args.description)
        if args.notes is not None:
            self.notes = self._normalize_argument(args.notes)

        # Process password entry-specific options.
        if args.card_number is not None:
            self.card_number = self._normalize_argument(args.card_number)
        if args.card_type is not None:
            self.card_type = self._normalize_argument(args.card_type)
        if args.ccv is not None:
            self.ccv = self._normalize_argument(args.ccv)
        if args.certificate is not None:
            self.certificate = self._normalize_argument(args.certificate)
        if args.code is not None:
            self.code = self._normalize_argument(args.code)
        if args.database is not None:
            self.database = self._normalize_argument(args.database)
        if args.domain is not None:
            self.domain = self._normalize_argument(args.domain)
        if args.email is not None:
            self.email = self._normalize_argument(args.email)
        if args.expiry_date is not None:
            self.expiry_date = self._normalize_argument(args.expiry_date)
        if args.hostname is not None:
            self.hostname = self._normalize_argument(args.hostname)
        if args.keyfile is not None:
            self.keyfile = self._normalize_argument(args.keyfile)
        if args.location is not None:
            self.location = self._normalize_argument(args.location)
        if args.password is not None:
            password = getpass.getpass("Entry password: ")
            self.password = self._normalize_argument(password)
        if args.phone_number is not None:
            self.phone_number = self._normalize_argument(args.phone_number)
        if args.pin is not None:
            self.pin = self._normalize_argument(args.pin)
        if args.port is not None:
            self.port = self._normalize_argument(args.port)
        if args.url is not None:
            self.url = self._normalize_argument(args.url)
        if args.username is not None:
            self.username = self._normalize_argument(args.username)

        # Finally, set the updated value.
        self.updated = storepass.util.get_current_datetime()

    def get_entry(self):
        """Obtain a new entry based on the set properties."""
        if self.type == 'folder':
            return storepass.model.Folder(self.name, self.description,
                                          self.updated, self.notes, [])
        if self.type == 'credit-card':
            return storepass.model.CreditCard(self.name, self.description,
                                              self.updated, self.notes,
                                              self.card_type, self.card_number,
                                              self.expiry_date, self.ccv,
                                              self.pin)
        if self.type == 'crypto-key':
            return storepass.model.CryptoKey(self.name, self.description,
                                             self.updated, self.notes,
                                             self.hostname, self.certificate,
                                             self.keyfile, self.password)
        if self.type == 'database':
            return storepass.model.Database(self.name, self.description,
                                            self.updated, self.notes,
                                            self.hostname, self.username,
                                            self.password, self.database)
        if self.type == 'door':
            return storepass.model.Door(self.name, self.description,
                                        self.updated, self.notes,
                                        self.location, self.code)
        if self.type == 'email':
            return storepass.model.Email(self.name, self.description,
                                         self.updated, self.notes, self.email,
                                         self.hostname, self.username,
                                         self.password)
        if self.type == 'ftp':
            return storepass.model.FTP(self.name, self.description,
                                       self.updated, self.notes, self.hostname,
                                       self.port, self.username, self.password)
        if self.type == 'generic':
            return storepass.model.Generic(self.name, self.description,
                                           self.updated, self.notes,
                                           self.hostname, self.username,
                                           self.password)
        if self.type == 'phone':
            return storepass.model.Phone(self.name, self.description,
                                         self.updated, self.notes,
                                         self.phone_number, self.pin)
        if self.type == 'shell':
            return storepass.model.Shell(self.name, self.description,
                                         self.updated, self.notes,
                                         self.hostname, self.domain,
                                         self.username, self.password)
        if self.type == 'remote-desktop':
            return storepass.model.RemoteDesktop(self.name, self.description,
                                                 self.updated, self.notes,
                                                 self.hostname, self.port,
                                                 self.username, self.password)
        if self.type == 'vnc':
            return storepass.model.VNC(self.name, self.description,
                                       self.updated, self.notes, self.hostname,
                                       self.port, self.username, self.password)
        if self.type == 'website':
            return storepass.model.Website(self.name, self.description,
                                           self.updated, self.notes, self.url,
                                           self.username, self.email,
                                           self.password)

        assert 0 and "Unhandled entry type!"
        return None

    def visit_folder(self, folder):
        """Update generator properties from a folder entry."""

    def visit_credit_card(self, credit_card):
        """Update generator properties from a credit-card entry."""
        self.card_type = credit_card.card_type
        self.card_number = credit_card.card_number
        self.expiry_date = credit_card.expiry_date
        self.ccv = credit_card.ccv
        self.pin = credit_card.pin

    def visit_crypto_key(self, crypto_key):
        """Update generator properties from a crypto-key entry."""
        self.hostname = crypto_key.hostname
        self.certificate = crypto_key.certificate
        self.keyfile = crypto_key.keyfile
        self.password = crypto_key.password

    def visit_database(self, database):
        """Update generator properties from a database entry."""
        self.hostname = database.hostname
        self.username = database.username
        self.password = database.password
        self.database = database.database

    def visit_door(self, door):
        """Update generator properties from a door entry."""
        self.location = door.location
        self.code = door.code

    def visit_email(self, email):
        """Update generator properties from an email entry."""
        self.email = email.email
        self.hostname = email.hostname
        self.username = email.username
        self.password = email.password

    def visit_ftp(self, ftp):
        """Update generator properties from an FTP entry."""
        self.hostname = ftp.hostname
        self.port = ftp.port
        self.username = ftp.username
        self.password = ftp.password

    def visit_generic(self, generic):
        """Update generator properties from a generic account entry."""
        self.hostname = generic.hostname
        self.username = generic.username
        self.password = generic.password

    def visit_phone(self, phone):
        """Update generator properties from a phone entry."""
        self.phone_number = phone.phone_number
        self.pin = phone.pin

    def visit_shell(self, shell):
        """Update generator properties from a shell entry."""
        self.hostname = shell.hostname
        self.domain = shell.domain
        self.username = shell.username
        self.password = shell.password

    def visit_remote_desktop(self, remote_desktop):
        """Update generator properties from a remote-desktop entry."""
        self.hostname = remote_desktop.hostname
        self.port = remote_desktop.port
        self.username = remote_desktop.username
        self.password = remote_desktop.password

    def visit_vnc(self, vnc):
        """Update generator properties from a VNC entry."""
        self.hostname = vnc.hostname
        self.port = vnc.port
        self.username = vnc.username
        self.password = vnc.password

    def visit_website(self, website):
        """Update generator properties from a website entry."""
        self.url = website.url
        self.username = website.username
        self.email = website.email
        self.password = website.password


def _check_entry_name(args):
    """Validate an entry name specified on the command line."""
    # Reject an empty entry name.
    if args.entry == '':
        _logger.error("specified entry name is empty")
        return 1
    return 0


def _validate_show_command(args):
    """Pre-validate command-line options for the show command."""
    return _check_entry_name(args)


def _validate_add_command(args):
    """Pre-validate command-line options for the add command."""
    res = _check_entry_name(args)
    if res != 0:
        return res

    return _check_property_arguments(args, args.type)


def _validate_delete_command(args):
    """Pre-validate command-line options for the delete command."""
    return _check_entry_name(args)


def _validate_edit_command(args):
    """Pre-validate command-line options for the edit command."""
    res = _check_entry_name(args)
    if res != 0:
        return res

    # If no new type is specified on the command line then leave validation of
    # property arguments to _process_edit_command() when a type of the existing
    # entry is determined.
    if args.type is None:
        return 0

    return _check_property_arguments(args, args.type)


def _process_init_command(args, _model):
    """Handle the init command: create an empty password database."""
    assert args.command == 'init'

    # Keep the model empty and let the main() function write out the database.
    return 0


def _process_list_command(args, model):
    """Handle the list command: print short information about all entries."""
    assert args.command == 'list'

    plain_view = view.ListView()
    model.visit_all(plain_view)
    return 0


def _process_show_command(args, model):
    """Handle the show command: print detailed information about one entry."""
    assert args.command == 'show'

    # Find the entry specified on the command line.
    try:
        path_spec = storepass.model.path_string_to_spec(args.entry)
        entry = model.get_entry(path_spec)
    except storepass.exc.ModelException as e:
        _logger.error("%s", e)
        return 1

    detail_view = view.DetailView()
    entry.accept(detail_view, single=True)
    return 0


def _process_add_command(args, model):
    """Handle the add command: insert a new password entry."""
    assert args.command == 'add'

    # Create the entry specified on the command line.
    try:
        path_spec = storepass.model.path_string_to_spec(args.entry)
    except storepass.exc.ModelException as e:
        _logger.error("%s", e)
        return 1

    generator = _EntryGenerator(path_spec[-1])
    generator.set_from_args(args)
    new_entry = generator.get_entry()

    # Insert the new entry in the model.
    try:
        parent_entry = model.get_entry(path_spec[:-1])
        model.add_entry(new_entry, parent_entry)
    except storepass.exc.ModelException as e:
        _logger.error("%s", e)
        return 1
    return 0


def _process_edit_command(args, model):
    """Handle the edit command: modify an existing password entry."""
    assert args.command == 'edit'

    # Find the entry specified on the command line.
    try:
        path_spec = storepass.model.path_string_to_spec(args.entry)
        old_entry = model.get_entry(path_spec)
    except storepass.exc.ModelException as e:
        _logger.error("%s", e)
        return 1

    # If no new type is specified then validate that property arguments are
    # valid for the existing type.
    if args.type is None:
        res = _check_property_arguments(args, type(old_entry))
        if res != 0:
            return res

    # Create a replacement entry.
    generator = _EntryGenerator(path_spec[-1])
    generator.set_from_entry(old_entry)
    generator.set_from_args(args)
    new_entry = generator.get_entry()

    # Update the entry in the model.
    try:
        model.replace_entry(old_entry, new_entry)
    except storepass.exc.ModelException as e:
        _logger.error("%s", e)
        return 1
    return 0


def _process_delete_command(args, model):
    """Handle the delete command: remove a single password entry."""
    assert args.command == 'delete'

    # Delete the entry specified on the command line.
    try:
        path_spec = storepass.model.path_string_to_spec(args.entry)
        entry = model.get_entry(path_spec)
        model.remove_entry(entry)
    except storepass.exc.ModelException as e:
        _logger.error("%s", e)
        return 1

    return 0


def _process_dump_command(args, storage):
    """Handle the dump command: print the raw XML content of a database."""
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


def _check_property_arguments(args, type_):
    """
    Check validity of specified property arguments for a given entry type.

    Check that all type-related options specified on the command line are valid
    for a given entry type. An error is logged if some option is not available.
    Returns 0 if the check was successful, or 1 on failure.
    """
    assert args.command in ('add', 'edit')

    # Determine the entry class. It can be either specified via its name or
    # directly.
    if isinstance(type_, str):
        for entry_cls in storepass.model.ENTRY_TYPES:
            if entry_cls.entry_type_name == type_:
                break
        else:
            assert 0 and "Unhandled entry type!"
    else:
        assert issubclass(type_, storepass.model.Entry)
        entry_cls = type_

    res = 0
    for field in storepass.model.ENTRY_FIELDS:
        if field in args.properties and field not in entry_cls.entry_fields:
            _logger.error("option --%s is not valid for entry type '%s'",
                          field.name, entry_cls.entry_type_name)
            res = 1
    return res


class _PropertyAction(argparse.Action):
    def __init__(self, option_strings, dest, field, **kwargs):
        super().__init__(option_strings, dest, **kwargs)
        self._field = field

    def __call__(self, parser, namespace, values, option_string=None):
        # TODO Remove once all code is converted to use args.properties.
        if self.nargs == 0:
            setattr(namespace, self.dest, True)
        else:
            setattr(namespace, self.dest, values)

        namespace.properties[self._field] = values


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
    argument_validity = [(cls.entry_type_name,
                          [field.name for field in cls.entry_fields])
                         for cls in storepass.model.ENTRY_TYPES]
    add_edit_epilog = "option validity for entry types:\n" + "\n".join([
        f"  {name + ':':22}{', '.join(args) if len(args) > 0 else '--'}"
        for name, args in argument_validity
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

    type_choices = [cls.entry_type_name for cls in storepass.model.ENTRY_TYPES]
    add_parser.add_argument('--type',
                            choices=type_choices,
                            default='generic',
                            help="entry type (the default is generic)")
    edit_parser.add_argument('--type', choices=type_choices, help="entry type")

    # Add command-line arguments to set entry properties.
    for sub_parser in (add_parser, edit_parser):
        common_group = sub_parser.add_argument_group(
            "optional arguments valid for all entry types")
        common_group.add_argument(
            '--description',
            metavar='DESC',
            help="set the entry description to the specified value")
        common_group.add_argument(
            '--notes', help="set the entry notes to the specified value")

        account_group = sub_parser.add_argument_group(
            "optional arguments valid for specific entry types")
        sub_parser.set_defaults(properties={})
        for field in storepass.model.ENTRY_FIELDS:
            if field.is_protected:
                nargs = 0
                help_ = f"prompt for a value of the {field.name} property"
            else:
                nargs = None
                help_ = f"set the {field.name} property to the specified value"
            account_group.add_argument(
                '--' + field.name,
                metavar="VALUE",
                action=_PropertyAction,
                field=field,
                nargs=nargs,
                #default=argparse.SUPPRESS,
                help=help_)

    for sub_parser in (show_parser, add_parser, delete_parser, edit_parser):
        sub_parser.add_argument('entry',
                                metavar='ENTRY',
                                help="password entry")

    return parser


def main():
    """
    Run the CLI interface.

    Run the StorePass command line interface. Returns 0 if the execution was
    successful and a non-zero value otherwise.
    """

    # Parse the command-line arguments.
    parser = _build_parser()
    try:
        args = parser.parse_args()
    except SystemExit as e:
        return e.code

    # Do further command-specific checks of the command line options.
    if args.command == 'show':
        res = _validate_show_command(args)
    elif args.command == 'add':
        res = _validate_add_command(args)
    elif args.command == 'delete':
        res = _validate_delete_command(args)
    elif args.command == 'edit':
        res = _validate_edit_command(args)
    else:
        # No extra checks needed.
        res = 0

    # Bail out if any check failed.
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
