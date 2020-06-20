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

    def visit_generic(self, generic):
        """Print one-line information about a generic account entry."""
        indent = self._get_current_indent()
        hostname = (f" [{generic.hostname}]"
                    if generic.hostname is not None else "")
        description = (f": {generic.description}"
                       if generic.description is not None else "")
        print(f"{indent}- {generic.name}{hostname}{description}")


class DetailView(storepass.model.ModelVisitor):
    """View that shows detailed information about visited entries."""
    def _print_common_info(self, entry):
        """Process common entry properties and print their values."""
        if entry.description is not None:
            print(f"  - Description: {entry.description}")
        if entry.updated is not None:
            updated = entry.updated.astimezone().strftime('%c %Z')
            print(f"  - Last modified: {updated}")
        if entry.notes is not None:
            print(f"  - Notes: {entry.notes}")

    def visit_folder(self, folder):
        """Print detailed information about a folder entry."""
        print(f"+ {folder.name} (folder)")
        self._print_common_info(folder)

    def visit_generic(self, generic):
        """Print detailed information about a generic account entry."""
        print(f"+ {generic.name} (password entry)")
        if generic.hostname is not None:
            print(f"  - Hostname: {generic.hostname}")
        if generic.username is not None:
            print(f"  - Username: {generic.username}")
        if generic.password is not None:
            print(f"  - Password: {generic.password}")
        self._print_common_info(generic)
