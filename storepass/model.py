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

import enum

import storepass.exc


def path_string_to_spec(path_string):
    """
    Split a name of a password entry into a list of its path elements.

    Parse a name of a password entry and return a list of its path elements.
    Character '/' is expected as the path separator and '\' starts an escape
    sequence.
    """
    class _State(enum.IntEnum):
        NORMAL = 0
        ESCAPE = 1

    res = []
    state = _State.NORMAL
    element = ""
    for char in path_string:
        if state == _State.NORMAL:
            if char == '/':
                res.append(element)
                element = ""
            elif char == '\\':
                state = _State.ESCAPE
            else:
                element += char
        else:
            assert state == _State.ESCAPE
            # TODO Check that the character is '\' or '/'. Reject other escape
            # values.
            element += char
            state = _State.NORMAL
    res.append(element)

    if state == _State.ESCAPE:
        raise storepass.exc.ModelException(
            f"entry name '{path_string}' has an incomplete escape sequence at "
            f"its end")

    return res


def path_element_to_string(path_element):
    """Convert a single path element to its escaped string representation."""
    res = ""
    for char in path_element:
        if char == '\\':
            res += "\\\\"
        elif char == '/':
            res += "\\/"
        else:
            res += char
    return res


def path_spec_to_string(path_spec):
    """
    Convert a list of path elements to a name of a password entry.

    Escape a list of path elements, join them on character '/' and return the
    resulting string.
    """
    return "/".join([path_element_to_string(element) for element in path_spec])


class ModelVisitor:
    """
    Base data model visitor.

    Visitor support class for the data model. It integrates closely with the
    entry classes and allows tracking of data associated with the currently
    active entry path.
    """
    def __init__(self):
        """Initialize a model visitor."""
        self._path = []

    def enter_container(self, container, data):
        """Add a given container to the current path and record its data."""
        self._path.append((container, data))

    def leave_container(self):
        """Remove the topmost container from the current path."""
        self._path.pop()

    def get_path_data(self, container):
        """Obtain data associated with a specified container."""
        # Search the path in the reverse order because the common case is to
        # obtain data for the current topmost parent container.
        for i in reversed(self._path):
            if i[0] == container:
                return i[1]

        assert 0 and "Container is not on the current path!"
        return None


class Container:
    """Generic container."""
    def __init__(self, children):
        """Initialize a container."""
        self._children = sorted(children, key=lambda child: child.name)
        for child in self._children:
            assert child._parent is None
            child._parent = self

    @property
    def children(self):
        """Obtain child entries."""
        return self._children

    def _get_child_index(self, name):
        """Get a position of a given entry in the children list."""
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
        Obtain a child entry with a given name together with its index.

        Search for a child with a given name. Returns a 2-item tuple consisting
        of the child object and its index if the name was found and (None,
        number-of-children) otherwise.
        """
        index = self._get_child_index(name)
        if index < len(self._children):
            child = self._children[index]
            if child.name == name:
                return (child, index)
        return (None, index)

    def get_child(self, name):
        """
        Obtain a child entry with a given name.

        Search for a child with a given name. Returns a found entry if it
        exists and None otherwise.
        """
        child, _ = self._get_child_full(name)
        return child

    def add_child(self, child, is_move=False):
        """
        Add a new child entry.

        Add a new child entry to the container. If is_move is set then detach
        the entry first from its current parent. Returns True if the insertion
        was successful and False if a child with the same name already exists.
        """
        # Silence "Access to a protected member _parent of a client class".
        # pylint: disable=protected-access

        assert (child._parent is not None) == is_move

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
        """Detach a specified child entry from the container."""
        # Silence "Access to a protected member _parent of a client class".
        # pylint: disable=protected-access

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
    """Database root."""
    def __init__(self, children):
        """Initialize a database root."""
        Container.__init__(self, children)

    def get_path(self):
        """Obtain a trivial path to the database root."""
        return []

    def __str__(self, indent=""):
        res = indent + "Root:"
        for child in self._children:
            res += "\n" + child.__str__(indent + "  ")
        return res

    def accept(self, visitor, single=False):
        """
        Visit the root and its children.

        Call a given visitor to process the root and its children. If single
        is set to False then only the root object is visited.
        """
        parent_data = visitor.visit_root(self)
        if not single:
            self._accept_children(visitor, parent_data)


class Entry:
    """Database entry base class."""
    def __init__(self, name, description, updated, notes):
        """Initialize an abstract database entry."""
        # Parent container. The value is managed by the Container class.
        self._parent = None

        self._name = name
        self.description = description
        self.updated = updated
        self.notes = notes

    @property
    def parent(self):
        """Obtain the parent container."""
        return self._parent

    @property
    def name(self):
        """Obtain a name of the entry."""
        return self._name

    def get_path(self):
        """Obtain a full path from the database root to this entry."""
        if self._parent is None:
            return [self.name]
        return [self.name] + self._parent.get_path()

    def inline_str(self):
        """Get a string describing the entry properties."""
        return (f"name={self.name}, description={self.description}, "
                f"updated={self.updated}, notes={self.notes}")

    def __str__(self):
        return "Entry(" + self.inline_str() + ")"


class Folder(Entry, Container):
    """Password folder."""
    def __init__(self, name, description, updated, notes, children):
        """Initialize a password folder."""
        Container.__init__(self, children)
        Entry.__init__(self, name, description, updated, notes)

    def move_children_to(self, folder):
        """
        Move children from this folder to another one. The target folder must
        not yet have any children.
        """

        # Silence "Access to a protected member _children of a client class"
        # and "Access to a protected member _parent of a client class".
        # pylint: disable=protected-access

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
        """
        Visit the folder and its children.

        Call a given visitor to process the folder and its children. If single
        is set to False then only the folder object is visited.
        """
        parent_data = visitor.visit_folder(self)
        if not single:
            self._accept_children(visitor, parent_data)


class Account(Entry):
    """Account entry base class."""
    def __init__(self, name, description, updated, notes):
        """Initialize an abstract account entry."""
        Entry.__init__(self, name, description, updated, notes)


class Generic(Account):
    """Generic account entry."""
    def __init__(self, name, description, updated, notes, hostname, username,
                 password):
        """Initialize a generic account entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.username = username
        self.password = password

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Generic({parent}, hostname={self.hostname}, "
                f"username={self.username}, password={self.password})")

    def accept(self, visitor, _single=False):
        """
        Visit the generic account entry.

        Call a given visitor to process the generic account entry.
        """
        visitor.visit_generic(self)


class Model:
    """Database model."""
    def __init__(self):
        """Initialize a database model."""
        self._root = Root([])

    def load(self, storage):
        """Initialize the model using a specified storage object."""
        self._root = storage.read_tree()

    def save(self, storage, exclusive=False):
        """Save the model using a specified storage object."""
        storage.write_tree(self._root, exclusive)

    def get_entry(self, path_spec):
        """
        Find a specified entry.

        Search for an entry using a specified path. Returns a corresponding
        entry if the path is valid and throws ModelException otherwise. If
        path_spec is empty then the root object is returned.
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
        Add a new entry under a specified parent.

        Add an entry as a child of a specified parent. Throws ModelException if
        an entry with the same name already exists.
        """
        if not parent.add_child(new_entry):
            parent_path_spec = parent.get_path()
            path_string = path_spec_to_string(parent_path_spec +
                                              [new_entry.name])
            raise storepass.exc.ModelException(
                f"Entry '{path_string}' already exists")

    def move_entry(self, entry, new_parent):
        """
        Move a previously added entry under a new parent.

        Re-parent an entry under another container. Throws ModelException if an
        entry with the same name already exists.
        """
        # TODO Assert is not ancestor. Report an error in such a case?
        if not new_parent.add_child(entry, is_move=True):
            parent_path_spec = new_parent.get_path()
            path_string = path_spec_to_string(parent_path_spec + [entry.name])
            raise storepass.exc.ModelException(
                f"Entry '{path_string}' already exists")

    def remove_entry(self, entry):
        """
        Remove a specified entry.

        Detach a specified entry from its parent and remove it. Throws
        ModelException if the entry is a non-empty folder.
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
        Replace a specified entry with another one.

        Remove an old entry and add a new one instead. Throws ModelException if
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

        if (move_children and isinstance(old_entry, Folder) and
                isinstance(new_entry, Folder)):
            old_entry.move_children_to(new_entry)
        parent.remove_child(old_entry)
        res = parent.add_child(new_entry)
        assert res is True

    def visit_all(self, visitor):
        """
        Visit all password entries.

        Call a given visitor to recursively process all entries.
        """
        self._root.accept(visitor)
