# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""
Data model module.

Class diagram:
     ,-----------,    ,-------,
     | Container |    | Entry |
     '-----------'    '-------'
         ^   ^          ^   ^
         |   |          |   |
     ,---'   +---,  ,---'   '---,
     |           |  |           |
  ,------,    ,--------,   ,---------,
  | Root |    | Folder |   | Account |
  '------'    '--------'   '---------'
                             ^
                             |
       ,---------------------'
       |
  ,---------,
  | Generic |
  '---------'

All Entry's must hold a valid name identifying the Folder/Account. The name is
set when the entry is created and remains constant during a lifetime of the
object.
"""

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
            # TODO Check that the character is '\' or '/'. Reject other escape
            # values.
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


class ModelVisitor:
    def __init__(self):
        self._path = []

    def enter_container(self, container, data):
        self._path.append((container, data))

    def leave_container(self):
        self._path.pop()

    def get_path_data(self, container):
        """Obtain data associated with the specified container."""

        # Search the path in the reverse order because the common case is to
        # obtain data for the current parent.
        for i in reversed(self._path):
            if i[0] == container:
                return i[1]

        assert 0 and "Container not on the parent path!"


class Container:
    def __init__(self, children):
        self._children = sorted(children, key=lambda child: child.name)
        for child in self._children:
            assert child._parent is None
            child._parent = self

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

    def _get_child_full(self, name):
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

    def get_child(self, name):
        """
        Search for a child with the given name. Returns a found entry if it
        exists and None otherwise.
        """

        child, _ = self._get_child_full(name)
        return child

    def add_child(self, child, is_move=False):
        """
        Add a new child object. Returns True if the insertion was successful
        and False if a child with the same name already exists.
        """

        assert (child.parent is not None) == is_move

        old_child, index = self._get_child_full(child.name)
        if old_child is not None:
            return False

        # Adding a new child is possible. If this is a move then tell the
        # previous parent that the child should be detached.
        if is_move:
            child._parent.remove_child(child)
            assert child._parent is None

        self._children.insert(index, child)
        child._parent = self
        return True

    def remove_child(self, child):
        """Delete a specified child."""

        assert child._parent == self

        child2, index = self._get_child_full(child.name)
        assert child == child2

        self._children[index]._parent = None
        del self._children[index]

    def _accept_children(self, visitor, parent_data):
        """Visit all child entries."""

        visitor.enter_container(self, parent_data)
        for child in self._children:
            child.accept(visitor)
        visitor.leave_container()


class Root(Container):
    def __init__(self, children):
        Container.__init__(self, children)

    def get_path(self):
        return []

    def __str__(self, indent=""):
        res = indent + "Root:"
        for child in self._children:
            res += "\n" + child.__str__(indent + "  ")
        return res

    def accept(self, visitor, single=False):
        parent_data = visitor.visit_root(self)
        if not single:
            self._accept_children(visitor, parent_data)


class Entry:
    def __init__(self, name, description, updated, notes):
        # Parent container. The value is managed by the Container class.
        self._parent = None

        self._name = name
        self.description = description
        self.updated = updated
        self.notes = notes

    @property
    def parent(self):
        return self._parent

    @property
    def name(self):
        return self._name

    def get_path(self):
        if self._parent is None:
            return [self.name]
        return [self.name] + self._parent.get_path()

    def inline_str(self):
        return (f"name={self.name}, description={self.description}, "
                f"updated={self.updated}, notes={self.notes}")

    def __str__(self):
        return "Entry(" + self.inline_str() + ")"


class Folder(Entry, Container):
    def __init__(self, name, description, updated, notes, children):
        Container.__init__(self, children)
        Entry.__init__(self, name, description, updated, notes)

    def move_children_to(self, folder):
        """
        Move children from this folder to another one. The target folder must
        not yet have any children.
        """

        assert isinstance(folder, Folder)

        assert len(folder._children) == 0
        folder._children = self._children
        self._children = []
        for child in folder._children:
            child._parent = folder

    def __str__(self, indent=""):
        parent = super().inline_str()
        res = indent + f"Folder({parent}):"
        for child in self._children:
            res += "\n" + child.__str__(indent + "  ")
        return res

    def accept(self, visitor, single=False):
        parent_data = visitor.visit_folder(self)
        if not single:
            self._accept_children(visitor, parent_data)


class Account(Entry):
    def __init__(self, name, description, updated, notes):
        Entry.__init__(self, name, description, updated, notes)


class Generic(Account):
    def __init__(self, name, description, updated, notes, hostname, username, \
        password):
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.username = username
        self.password = password

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Generic({parent}, hostname={self.hostname}, "
                f"username={self.username}, password={self.password})")

    def accept(self, visitor, single=False):
        visitor.visit_generic(self)


class Model:
    def __init__(self):
        self._root = Root([])

    def load(self, storage):
        """Initialize the model using the specified storage object."""

        self._root = storage.read_tree()

    def save(self, storage, exclusive=False):
        """Save the model using the specified storage object."""

        storage.write_tree(self._root, exclusive)

    def get_entry(self, path_spec):
        """
        Search for a specified entry. Returns a found entry if it exists and
        throws ModelException otherwise.

        If path_spec is empty then the Root object is returned.
        """

        parent = None
        entry = self._root
        for i, element in enumerate(path_spec):
            parent = entry

            if not isinstance(parent, Container):
                element_string = path_element_to_string(element)
                path_string = path_spec_to_string(path_spec)
                raise storepass.exc.ModelException(
                    f"Entry '{element_string}' (element #{i+1} in "
                    f"'{path_string}') has a non-folder type")

            entry = parent.get_child(element)
            if entry is None:
                element_string = path_element_to_string(element)
                path_string = path_spec_to_string(path_spec)
                raise storepass.exc.ModelException(
                    f"Entry '{element_string}' (element #{i+1} in "
                    f"'{path_string}') does not exist")

        return entry

    def add_entry(self, new_entry, parent):
        """
        Add a new entry under a specified parent. Throws ModelException if an
        entry with the same name already exists.
        """

        if not parent.add_child(new_entry):
            parent_path_spec = parent.get_path()
            path_string = path_spec_to_string(parent_path_spec +
                                              [new_entry.name])
            raise storepass.exc.ModelException(
                f"Entry '{path_string}' already exists")

    def move_entry(self, entry, new_parent):
        """
        Move a previously added entry under a new parent. Throws ModelException
        if an entry with the same name already exists.
        """

        if not new_parent.add_child(entry, is_move=True):
            parent_path_spec = new_parent.get_path()
            path_string = path_spec_to_string(parent_path_spec + [entry.name])
            raise storepass.exc.ModelException(
                f"Entry '{path_string}' already exists")

    def remove_entry(self, entry):
        """
        Remove a specified entry. Throws ModelException if the entry is a
        non-empty folder.
        """

        if isinstance(entry, Container) and len(entry.children) > 0:
            path_string = path_spec_to_string(entry.get_path())
            raise storepass.exc.ModelException(
                f"Entry '{path_string}' is not empty")

        parent = entry.parent
        assert parent is not None
        parent.remove_child(entry)

    def replace_entry(self, old_entry, new_entry, move_children=True):
        """
        Replace a specified entry with another one. Throws ModelException if
        the new entry has a same name as an already existing entry and it is
        not the old entry.

        If move_children is True and the entries are both Folder's then the
        code moves all children rooted at the old entry to the new one.
        """

        parent = old_entry.parent
        assert parent is not None

        if old_entry.name != new_entry.name:
            child = parent.get_child(new_entry.name)
            if child is not None:
                path_string = path_spec_to_string(parent.get_path() +
                                                  [new_entry.name])
                raise storepass.exc.ModelException(
                    f"Entry '{path_string}' already exists")

        if move_children and isinstance(old_entry, Folder) and \
            isinstance(new_entry, Folder):
            old_entry.move_children_to(new_entry)
        parent.remove_child(old_entry)
        res = parent.add_child(new_entry)
        assert res is True

    def visit_all(self, visitor):
        """
        Iterate over all password entries and pass them individually to the
        specified visitor.
        """

        self._root.accept(visitor)
