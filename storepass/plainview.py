# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

class PlainView:
    def __init__(self):
        self._parent_chain = []

    def _backtrace_parent(self, parent):
        while self._parent_chain[-1] != parent:
            del self._parent_chain[-1]

    def visit_folder(self, parent, folder):
        if parent is None:
            assert len(self._parent_chain) == 0
        else:
            self._backtrace_parent(parent)

        print("  " * len(self._parent_chain) + f"+ {folder.name}")
        self._parent_chain.append(folder)

    def visit_generic(self, parent, generic):
        assert len(self._parent_chain) > 0
        self._backtrace_parent(parent)

        print("  " * len(self._parent_chain) + f"- {generic.name}: {generic.name}, {generic.password}")
