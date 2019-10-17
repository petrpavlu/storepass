# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

class Node:
    def __init__(self, name, description, updated, notes):
        self.name = name
        self.description = description
        self.updated = updated
        self.notes = notes

    def inline_str(self):
        return f"name={self.name}, description={self.description}, updated={self.updated}, notes={self.notes}"

    def __str__(self):
        return "Node(" + self.inline_str() + ")"

class Folder(Node):
    def __init__(self, name, description, updated, notes):
        super().__init__(name, description, updated, notes)
        self._children = []

    def append(self, child):
        self._children.append(child)

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

class Generic(Node):
    def __init__(self, name, description, updated, notes, username, password):
        super().__init__(name, description, updated, notes)
        self.username = username
        self.password = password

    def __str__(self, indent=""):
        parent = super().inline_str()
        return indent + f"Generic({parent}, username={self.username}, password={self.password})"

    def visit(self, view, parent):
        view.visit_generic(parent, self)

class Model:
    def __init__(self):
        self._root = None

    def load(self, storage):
        storage_node = storage.read_tree()
        self._root = self._load_storage_node(storage_node)

    def _load_storage_node(self, storage_node):
        attributes = storage_node.attributes
        print(attributes)

        if storage_node.type in \
            (storage_node.TYPE_ROOT, storage_node.TYPE_FOLDER):
            new_node = Folder('TODO', 'TODO', 'TODO', 'TODO')
            for storage_child in storage_node.children:
                new_node.append(self._load_storage_node(storage_child))
        else:
            assert storage_node.type == storage_node.TYPE_GENERIC
            new_node = Generic('TODO', 'TODO', 'TODO', 'TODO', 'TODO', 'TODO')

        return new_node

    def visit_all(self, view):
        if self._root is not None:
            self._root.visit(view, None)
