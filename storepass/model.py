# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import storepass.exc


def path_string_to_spec(path_string):
    """
    Split a name of a password entry and return a list of its path elements.
    Character '/' is expected as the path separator and '\' starts an escape
    sequence.
    """

    STATE_NORMAL = 0
    STATE_ESCAPE = 1

    res = []
    state = STATE_NORMAL
    element = ""
    for c in path_string:
        if state == STATE_NORMAL:
            if c == '/':
                res.append(element)
                element = ""
            elif c == '\\':
                state = STATE_ESCAPE
            else:
                element += c
        else:
            assert state == STATE_ESCAPE
            element += c
            state = STATE_NORMAL
    res.append(element)

    if state == STATE_ESCAPE:
        raise ModelException(
            f"entry name '{path_string}' has an incomplete escape sequence at "
            f"its end")

    return res


def path_element_to_string(path_element):
    """Convert a single path element to its escaped string representation."""

    res = ""
    for c in path_element:
        if c == '\\':
            res += "\\\\"
        elif c == '/':
            res += "\\/"
        else:
            res += c
    return res


def path_spec_to_string(path_spec):
    """
    Convert a list of path elements to its escaped and joined string
    representation.
    """

    return "/".join([path_element_to_string(element) for element in path_spec])


class Container:
    def __init__(self, children):
        self._children = sorted(children, key=lambda child: child.name)

    @property
    def children(self):
        return self._children

    def _get_child_index(self, name):
        low = 0
        high = len(self._children)
        while low < high:
            mid = (low + high) // 2
            if self._children[mid].name < name:
                low = mid + 1
            else:
                high = mid
        return low

    def get_child(self, name):
        index = self._get_child_index(name)
        if index < len(self._children):
            child = self._children[index]
            if child.name == name:
                return (child, index)
        return (None, index)

    def add_child(self, child):
        old_child, index = self.get_child(child.name)
        if old_child is not None:
            raise 0  # TODO
        self._children.insert(index, child)


class Root(Container):
    def __init__(self, children):
        Container.__init__(self, children)

    def __str__(self, indent=""):
        res = indent + "Root:"
        for child in self._children:
            res += "\n" + child.__str__(indent + "  ")
        return res

    def accept(self, visitor):
        visitor.visit_root(None, self)
        for child in self._children:
            child.accept(visitor, self)


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


class Folder(Entry, Container):
    def __init__(self, name, description, updated, notes, children):
        Container.__init__(self, children)
        Entry.__init__(self, name, description, updated, notes)

    def __str__(self, indent=""):
        parent = super().inline_str()
        res = indent + f"Folder({parent}):"
        for child in self._children:
            res += "\n" + child.__str__(indent + "  ")
        return res

    def accept(self, visitor, parent):
        visitor.visit_folder(parent, self)
        for child in self._children:
            child.accept(visitor, self)


class Generic(Entry):
    def __init__(self, name, description, updated, notes, hostname, username, \
        password):
        Entry.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.username = username
        self.password = password

    def __str__(self, indent=""):
        parent = super().inline_str()
        return indent + f"Generic({parent}, hostname={self.hostname}, username={self.username}, password={self.password})"

    def accept(self, visitor, parent):
        visitor.visit_generic(parent, self)


class Model:
    def __init__(self):
        self._root = Root([])

    def load(self, storage):
        """Initialize the model using the specified storage object."""

        self._root = storage.read_tree()

    def save(self, storage, exclusive=False):
        storage.write_tree(self._root, exclusive)

    def add_entry(self, parent_path_spec, entry):
        """Insert a new entry at the specified path."""

        parent_entry = self.get_entry(parent_path_spec)
        parent_entry.add_child(entry)

    def get_entry(self, path_spec):
        """Search for a specified entry."""

        entry = self._root
        for i, element in enumerate(path_spec):
            if not isinstance(entry, Container):
                element_string = path_element_to_string(element)
                path_string = path_spec_to_string(path_spec)
                raise storepass.exc.ModelException(
                    f"Entry '{element_string}' (element #{i+1} in "
                    f"'{path_string}') has a non-folder type")

            for j in entry.children:
                if j.name == element:
                    entry = j
                    break
            else:
                element_string = path_element_to_string(element)
                path_string = path_spec_to_string(path_spec)
                raise storepass.exc.ModelException(
                    f"Entry '{element_string}' (element #{i+1} in "
                    f"'{path_string}') does not exist")

        return entry

    def visit_all(self, visitor):
        """
        Iterate over all password entries and pass them individually to the
        specified visitor.
        """

        if self._root is not None:
            self._root.accept(visitor)
