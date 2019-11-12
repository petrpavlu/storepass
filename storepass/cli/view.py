# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Textual views suitable for the console."""

class ListView:
    """
    View for producing a tree-like list with one-line information about each
    password entry.
    """

    def __init__(self):
        self._parent_chain = []

    def _backtrace_parent(self, parent):
        assert parent is not None
        assert len(self._parent_chain) > 0

        while self._parent_chain[-1] != parent:
            del self._parent_chain[-1]

    def visit_root(self, parent, root):
        assert parent is None
        assert len(self._parent_chain) == 0

        self._parent_chain.append(root)

    def _get_current_indent(self):
        return "  " * (len(self._parent_chain) - 1)

    def visit_folder(self, parent, folder):
        self._backtrace_parent(parent)

        indent = self._get_current_indent()
        description = f": {folder.description}" \
            if folder.description is not None else ""
        print(f"{indent}+ {folder.name}{description}")
        self._parent_chain.append(folder)

    def visit_generic(self, parent, generic):
        self._backtrace_parent(parent)

        indent = self._get_current_indent()
        hostname = f" [{generic.hostname}]" \
            if generic.hostname is not None else ""
        description = f": {generic.description}" \
            if generic.description is not None else ""
        print(f"{indent}- {generic.name}{hostname}{description}")

class DetailView:
    def _print_common_info(self, entry):
        if entry.description is not None:
            print(f"  - Description: {entry.description}")
        if entry.updated is not None:
            print(f"  - Last modified: {entry.updated}")
        if entry.notes is not None:
            print(f"  - Notes: {entry.notes}")

    def visit_folder(self, parent, folder):
        print(f"+ {folder.name} (folder)")
        self._print_common_info(folder)

    def visit_generic(self, parent, generic):
        print(f"+ {generic.name} (password entry)")
        if generic.username is not None:
            print(f"  - Username: {generic.username}")
        if generic.password is not None:
            print(f"  - Password: {generic.password}")
        if generic.hostname is not None:
            print(f"  - Hostname: {generic.hostname}")
        self._print_common_info(generic)
