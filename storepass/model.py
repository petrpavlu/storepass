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
        """
        Search for a child with the given name. Returns a 2-item tuple
        consisting of the child object and its index if the name was found and
        (None, number-of-children) otherwise.
        """

        index = self._get_child_index(name)
        if index < len(self._children):
            child = self._children[index]
            if child.name == name:
                return (child, index)
        return (None, index)

    def add_child(self, child):
        """
        Add a new child object. Returns True if the insertion was successful and
        False if a child with the same name already exists.
        """

        old_child, index = self.get_child(child.name)
        if old_child is not None:
            return False
        self._children.insert(index, child)
        return True

    def delete_child(self, index):
        """Delete a child at the given index."""

        del self._children[index]


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
        """Save the model using the specified storage object."""

        storage.write_tree(self._root, exclusive)

    def get_entry_full(self, path_spec):
        """
        Search for a specified entry. Returns a 3-item tuple consisting of the
        found entry, its parent and entry's index in the parent's children if
        the entry exists and throws ModelException otherwise.
        """

        parent = None
        entry = self._root
        parent_index = 0
        for i, element in enumerate(path_spec):
            parent = entry

            if not isinstance(parent, Container):
                element_string = path_element_to_string(element)
                path_string = path_spec_to_string(path_spec)
                raise storepass.exc.ModelException(
                    f"Entry '{element_string}' (element #{i+1} in "
                    f"'{path_string}') has a non-folder type")

            entry, parent_index = parent.get_child(element)
            if entry is None:
                element_string = path_element_to_string(element)
                path_string = path_spec_to_string(path_spec)
                raise storepass.exc.ModelException(
                    f"Entry '{element_string}' (element #{i+1} in "
                    f"'{path_string}') does not exist")

        return entry, parent, parent_index

    def get_entry(self, path_spec):
        """Wrapper for get_entry_full() that returns only the found entry."""

        entry, _, _ = self.get_entry_full(path_spec)
        return entry

    def add_entry(self, parent_path_spec, entry):
        """
        Insert a new entry at the specified path. Throws ModelException if the
        parent path is not valid or the entry already exists.
        """

        parent_entry = self.get_entry(parent_path_spec)
        if not parent_entry.add_child(entry):
            path_string = path_element_to_string(
                parent_path_spec + [entry.name])
            raise storepass.exc.ModelException(
                f"Entry '{path_string}' already exists")

    def delete_entry(self, path_spec):
        """
        Delete a specified entry. Throws ModelException if the entry does not
        exist or is a non-empty folder.
        """

        entry, parent, parent_index = self.get_entry_full(path_spec)
        # TODO Check that the entry is empty.
        parent.delete_child(parent_index)

    def visit_all(self, visitor):
        """
        Iterate over all password entries and pass them individually to the
        specified visitor.
        """

        self._root.accept(visitor)
