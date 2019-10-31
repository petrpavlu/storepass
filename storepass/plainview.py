# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

class PlainView:
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

    def visit_folder(self, parent, folder):
        self._backtrace_parent(parent)

        print("  " * (len(self._parent_chain) - 1) + f"+ {folder.name}")
        self._parent_chain.append(folder)

    def visit_generic(self, parent, generic):
        self._backtrace_parent(parent)

        print("  " * (len(self._parent_chain) - 1) + f"- {generic.name}: {generic.name}, {generic.password}")
