# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Textual views suitable for the console."""

import storepass.model


class ListView(storepass.model.ModelVisitor):
    """View that produces a tree with one-line about each visited entry."""
    def visit_root(self, root):
        """Process the database root."""
        # Do nothing.

    def _get_current_indent(self):
        """Obtain current indentation."""
        return "  " * (len(self._path) - 1)

    def visit_folder(self, folder):
        """Print one-line information about a folder entry."""
        indent = self._get_current_indent()
        description = (f": {folder.description}"
                       if folder.description is not None else "")
        print(f"{indent}+ {folder.name}{description}")

    def visit_account(self, account):
        """Print one-line information about an account entry."""
        indent = self._get_current_indent()
        if storepass.model.HOSTNAME_FIELD in account.entry_fields:
            address = account.properties[storepass.model.HOSTNAME_FIELD]
        elif storepass.model.URL_FIELD in account.entry_fields:
            address = account.properties[storepass.model.URL_FIELD]
        else:
            address = None
        address = f" [{address}]" if address is not None else ""
        description = (f": {account.description}"
                       if account.description is not None else "")
        print(f"{indent}- {account.name}{address}{description}")


class DetailView(storepass.model.ModelVisitor):
    """View that shows detailed information about visited entries."""
    def visit_entry(self, entry):
        """Print detailed information about an entry."""
        print(f"+ {entry.get_full_name()} ({entry.entry_label})")

        # Process entry-specific properties and print their values.
        for field in entry.entry_fields:
            value = entry.properties[field]
            if value is not None:
                print(f"  - {field.label}: {value}")

        # Process common entry properties and print their values.
        if entry.description is not None:
            print(f"  - Description: {entry.description}")
        if entry.updated is not None:
            updated = entry.updated.astimezone().strftime('%c %Z')
            print(f"  - Last modified: {updated}")
        if entry.notes is not None:
            print(f"  - Notes: {entry.notes}")
