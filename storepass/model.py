# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

class Root:
    def __init__(self, children):
        self._children = children

    @property
    def children(self):
        return self._children

    def __str__(self, indent=""):
        for child in self._children:
            res += child.__str__(indent) + "\n"
        return res

    def visit(self, view, parent):
        view.visit_root(parent, self)
        for child in self._children:
            child.visit(view, self)

class Entry:
    def __init__(self, name, description, updated, notes):
        self.name = name
        self.description = description
        self.updated = updated
        self.notes = notes

    def inline_str(self):
        return f"name={self.name}, description={self.description}, updated={self.updated}, notes={self.notes}"

    def __str__(self):
        return "Entry(" + self.inline_str() + ")"

class Folder(Entry):
    def __init__(self, name, description, updated, notes, children):
        super().__init__(name, description, updated, notes)
        self._children = children

    @property
    def children(self):
        return self._children

    def __str__(self, indent=""):
        parent = super().inline_str()
        res = indent + f"Folder({parent}):"
        for child in self._children:
            res += "\n" + child.__str__(indent + "  ")
        return res

    def visit(self, view, parent):
        view.visit_folder(parent, self)
        for child in self._children:
            child.visit(view, self)

class Generic(Entry):
    def __init__(self, name, description, updated, notes, hostname, username, \
        password):
        super().__init__(name, description, updated, notes)
        self.hostname = hostname
        self.username = username
        self.password = password

    def __str__(self, indent=""):
        parent = super().inline_str()
        return indent + f"Generic({parent}, hostname={self.hostname}, username={self.username}, password={self.password})"

    def visit(self, view, parent):
        view.visit_generic(parent, self)

class Model:
    def __init__(self):
        self._root = None

    def load(self, storage):
        """Initialize the model using the specified storage object."""

        self._root = storage.read_tree()

    def get_entry(self, path_spec):
        entry = self._root
        for element in path_spec:
            if not isinstance(entry, Root) and not isinstance(entry, Folder):
                return None

            for i in entry.children:
                if i.name == element:
                    entry = i
                    break
            else:
                return None

        return entry

    def visit_all(self, view):
        """
        Iterate over all password entries and pass them individually to the
        specified view visitor.
        """

        if self._root is not None:
            self._root.visit(view, None)
