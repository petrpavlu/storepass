# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Textual views suitable for the console."""

import storepass.model


class ListView(storepass.model.ModelVisitor):
    """
    View for producing a tree-like list with one-line information about each
    password entry.
    """
    def visit_root(self, root):
        # Do nothing.
        pass

    def _get_current_indent(self):
        return "  " * (len(self._path) - 1)

    def visit_folder(self, folder):
        indent = self._get_current_indent()
        description = f": {folder.description}" \
            if folder.description is not None else ""
        print(f"{indent}+ {folder.name}{description}")

    def visit_generic(self, generic):
        indent = self._get_current_indent()
        hostname = f" [{generic.hostname}]" \
            if generic.hostname is not None else ""
        description = f": {generic.description}" \
            if generic.description is not None else ""
        print(f"{indent}- {generic.name}{hostname}{description}")


class DetailView(storepass.model.ModelVisitor):
    def _print_common_info(self, entry):
        if entry.description is not None:
            print(f"  - Description: {entry.description}")
        if entry.updated is not None:
            updated = entry.updated.astimezone().strftime('%c %Z')
            print(f"  - Last modified: {updated}")
        if entry.notes is not None:
            print(f"  - Notes: {entry.notes}")

    def visit_folder(self, folder):
        print(f"+ {folder.name} (folder)")
        self._print_common_info(folder)

    def visit_generic(self, generic):
        print(f"+ {generic.name} (password entry)")
        if generic.hostname is not None:
            print(f"  - Hostname: {generic.hostname}")
        if generic.username is not None:
            print(f"  - Username: {generic.username}")
        if generic.password is not None:
            print(f"  - Password: {generic.password}")
        self._print_common_info(generic)
