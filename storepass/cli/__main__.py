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

_logger = logging.getLogger(__name__)

_NAME_TO_ENTRY_TYPE_MAP = {
    cls.entry_type_name: cls
    for cls in storepass.model.ENTRY_TYPES
}


class _EntryGenerator:
    """Generator to create a new entry."""
    def __init__(self, name):
        """Initialize an entry generator."""
        self.type_cls = None

        self.name = name
        self.description = None
        self.updated = None
        self.notes = None
        self.properties = {}

    def _normalize_argument(self, value):
        """Normalize an argument value to None if it is an empty string."""
        return storepass.util.normalize_empty_to_none(value)

    def _update_property(self, field, value):
        """Update a value of a specified property."""
        if value is not None:
            self.properties[field] = value
        elif field in self.properties:
            del self.properties[field]

    def set_from_entry(self, entry):
        """Update properties from an existing entry."""
        self.type_cls = type(entry)

        self.description = entry.description
        self.updated = entry.updated
        self.notes = entry.notes
        for field in entry.entry_fields:
            self._update_property(field, entry.properties[field])

    def set_from_args(self, args):
        """Update properties from command line arguments."""
        if args.type is not None:
            self.type_cls = _NAME_TO_ENTRY_TYPE_MAP[args.type]

        # Process options valid for all entries.
        if args.description is not None:
            self.description = self._normalize_argument(args.description)
        if args.notes is not None:
            self.notes = self._normalize_argument(args.notes)

        # Process entry-specific options.
        for field, value in args.properties.items():
            if field.is_protected:
                value = getpass.getpass(f"Entry {field.name}: ")
            self._update_property(field, self._normalize_argument(value))

        # Finally, set the updated value.
        self.updated = storepass.util.get_current_datetime()

    def get_entry(self):
        """Obtain a new entry based on the set properties."""
        # Filter out any fields that are invalid for the type of a new entry.
        properties = {
            field: value
            for field, value in self.properties.items()
            if field in self.type_cls.entry_fields
        }

        return self.type_cls.from_proxy(self.name, self.description,
                                        self.updated, self.notes, properties)


def _check_entry_name(args):
    """Validate an entry name specified on the command line."""
    # Reject an empty entry name.
    if args.entry == '':
        print("Specified entry name is empty", file=sys.stderr)
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
        print(f"{e}", file=sys.stderr)
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
        print(f"{e}", file=sys.stderr)
        return 1

    generator = _EntryGenerator(path_spec[-1])
    generator.set_from_args(args)
    new_entry = generator.get_entry()

    # Insert the new entry in the model.
    try:
        parent_entry = model.get_entry(path_spec[:-1])
        model.add_entry(new_entry, parent_entry)
    except storepass.exc.ModelException as e:
        print(f"{e}", file=sys.stderr)
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
        print(f"{e}", file=sys.stderr)
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
        print(f"{e}", file=sys.stderr)
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
        print(f"{e}", file=sys.stderr)
        return 1

    return 0


def _process_dump_command(args, storage):
    """Handle the dump command: print the raw XML content of a database."""
    assert args.command == 'dump'

    # Load the database content.
    try:
        plain_data = storage.read_plain()
    except storepass.exc.StorageReadException as e:
        print(f"Failed to load password database '{args.file}': {e}")
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
        entry_cls = _NAME_TO_ENTRY_TYPE_MAP[type_]
    else:
        assert issubclass(type_, storepass.model.Entry)
        entry_cls = type_

    res = 0
    for field in storepass.model.ENTRY_FIELDS:
        if field in args.properties and field not in entry_cls.entry_fields:
            print(
                f"Property '{field.name}' is not valid for entry type "
                f"'{entry_cls.entry_type_name}'",
                file=sys.stderr)
            res = 1
    return res


class _ArgumentParser(argparse.ArgumentParser):
    """Command-line argument parser."""
    def error(self, message):
        """Report a specified error message and exit the program."""
        self.exit(2, f"Input error: {message}\n")


class _PropertyAction(argparse.Action):
    def __init__(self, option_strings, dest, field, **kwargs):
        super().__init__(option_strings, dest, **kwargs)
        self._field = field

    def __call__(self, parser, namespace, values, option_string=None):
        namespace.properties[self._field] = values


def _build_parser():
    """Create and initialize a command-line parser."""
    parser = _ArgumentParser()
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
    argument_validity = [(name, [field.name for field in cls.entry_fields])
                         for name, cls in _NAME_TO_ENTRY_TYPE_MAP.items()]
    add_edit_epilog = "property validity for entry types:\n" + "\n".join([
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

    add_parser.add_argument('--type',
                            choices=_NAME_TO_ENTRY_TYPE_MAP.keys(),
                            default='generic',
                            help="entry type (the default is generic)")
    edit_parser.add_argument('--type',
                             choices=_NAME_TO_ENTRY_TYPE_MAP.keys(),
                             help="entry type")

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
        # Set the level for the root logger.
        logging.getLogger().setLevel(level)
        _logger.info("Log verbosity set to '%s'", level)

    # Handle the specified command.
    if args.command is None:
        print("No command specified", file=sys.stderr)
        return 1

    _logger.debug("Processing command '%s' on file '%s'", args.command,
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
            print(f"Failed to load password database '{args.file}': {e}",
                  file=sys.stderr)
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
            print(f"Failed to save password database '{args.file}': {e}",
                  file=sys.stderr)
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
