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
     ,---'   '---,  ,---'   '---,
     |           |  |           |
  ,------,    ,--------,   ,---------,
  | Root |    | Folder |   | Account |
  '------'    '--------'   '---------'
                                ^
                                |
        ,--------------,--------+-------,----------,---------,--------,
        |              |        |       |          |         |        |
  ,------------, ,-----------,  |  ,----------, ,------, ,-------, ,-----,
  | CreditCard | | CryptoKey |  |  | Database | | Door | | Email | | FTP |
  '------------' '-----------'  |  '----------' '------' '-------' '-----'
                                |
       ,----------,---------,---'---------,------------,---------,
       |          |         |             |            |         |
  ,---------, ,-------, ,-------, ,---------------, ,-----, ,---------,
  | Generic | | Phone | | Shell | | RemoteDesktop | | VNC | | Website |
  '---------' '-------' '-------' '---------------' '-----' '---------'

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
    Character '/' is expected as the path separator and '\\' starts an escape
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


class Field:
    """Entry field."""
    def __init__(self, name):
        """Initialize an account field."""
        self.name = name


CARD_NUMBER_FIELD = Field('card-number')
CARD_TYPE_FIELD = Field('card-type')
CCV_FIELD = Field('ccv')
CERTIFICATE_FIELD = Field('certificate')
CODE_FIELD = Field('code')
DATABASE_FIELD = Field('database')
DOMAIN_FIELD = Field('domain')
EMAIL_FIELD = Field('email')
EXPIRY_DATE_FIELD = Field('expiry-date')
HOSTNAME_FIELD = Field('hostname')
KEYFILE_FIELD = Field('keyfile')
LOCATION_FIELD = Field('location')
PASSWORD_FIELD = Field('password')
PHONE_NUMBER_FIELD = Field('phone-number')
PIN_FIELD = Field('pin')
PORT_FIELD = Field('port')
URL_FIELD = Field('url')
USERNAME_FIELD = Field('username')

ENTRY_FIELDS = (
    CARD_NUMBER_FIELD,
    CARD_TYPE_FIELD,
    CCV_FIELD,
    CERTIFICATE_FIELD,
    CODE_FIELD,
    DATABASE_FIELD,
    DOMAIN_FIELD,
    EMAIL_FIELD,
    EXPIRY_DATE_FIELD,
    HOSTNAME_FIELD,
    KEYFILE_FIELD,
    LOCATION_FIELD,
    PASSWORD_FIELD,
    PHONE_NUMBER_FIELD,
    PIN_FIELD,
    PORT_FIELD,
    URL_FIELD,
    USERNAME_FIELD,
)


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

    def get_full_name(self):
        """Obtain a trivial full name of the database root."""
        return ''

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

    _entry_type_name = 'entry'
    _entry_fields = ()

    class _PropertyProxy:
        def __init__(self, entry):
            self.entry = entry

        def __getitem__(self, field):
            return self.entry._get_field(field)

        def __setitem__(self, field, value):
            self.entry._set_field(field, value)

    def __init__(self, name, description, updated, notes):
        """Initialize an abstract database entry."""
        assert name is not None
        assert name != ''

        # Parent container. The value is managed by the Container class.
        self._parent = None

        self._name = name
        self.description = description
        self.updated = updated
        self.notes = notes
        self.properties = self._PropertyProxy(self)

    @classmethod
    def get_entry_type_name(cls):
        """Obtain a name of the entry type."""
        return cls._entry_type_name

    @classmethod
    def get_entry_fields(cls):
        """Obtain property fields for the entry type."""
        return cls._entry_fields

    @property
    def parent(self):
        """Obtain the parent container."""
        return self._parent

    @property
    def name(self):
        """Obtain a name of the entry."""
        return self._name

    def _get_field(self, field):
        """Get a value of a specified field."""
        assert 0 and "Unimplemented method _get_field()!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        assert 0 and "Unimplemented method _set_field()!"

    def get_path(self):
        """Obtain a full path from the database root to the entry."""
        if self._parent is None:
            return [self.name]
        return self._parent.get_path() + [self.name]

    def get_full_name(self):
        """Obtain a full name of the entry."""
        return path_spec_to_string(self.get_path())

    def inline_str(self):
        """Get a string describing the entry properties."""
        return (f"name={self.name}, description={self.description}, "
                f"updated={self.updated}, notes={self.notes}")

    def __str__(self):
        return "Entry(" + self.inline_str() + ")"


class Folder(Entry, Container):
    """Password folder."""
    _entry_type_name = 'folder'
    _entry_fields = ()

    def __init__(self, name, description, updated, notes, children):
        """Initialize a password folder."""
        Container.__init__(self, children)
        Entry.__init__(self, name, description, updated, notes)

    def _get_field(self, field):
        """Get a value of a specified field."""
        assert 0 and "Invalid Folder field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        assert 0 and "Invalid Folder field!"

    def move_children_to(self, container):
        """
        Move children from this folder to another container.

        Re-parent the current children under another container. The target
        container must not have any children yet.
        """
        # Silence "Access to a protected member _children of a client class"
        # and "Access to a protected member _parent of a client class".
        # pylint: disable=protected-access

        assert isinstance(container, Container)

        assert len(container._children) == 0
        container._children = self._children
        self._children = []
        for child in container._children:
            child._parent = container

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


class CreditCard(Account):
    """Credit card entry."""
    _entry_type_name = 'credit-card'
    _entry_fields = (CARD_TYPE_FIELD, CARD_NUMBER_FIELD, EXPIRY_DATE_FIELD,
                     CCV_FIELD, PIN_FIELD)

    def __init__(self, name, description, updated, notes, card_type,
                 card_number, expiry_date, ccv, pin):
        """Initialize a credit card entry."""
        Account.__init__(self, name, description, updated, notes)
        self.card_type = card_type
        self.card_number = card_number
        self.expiry_date = expiry_date
        self.ccv = ccv
        self.pin = pin

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == CARD_TYPE_FIELD:
            return self.card_type
        if field == CARD_NUMBER_FIELD:
            return self.card_number
        if field == EXPIRY_DATE_FIELD:
            return self.expiry_date
        if field == CCV_FIELD:
            return self.ccv
        if field == PIN_FIELD:
            return self.pin
        assert 0 and "Invalid CreditCard field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == CARD_TYPE_FIELD:
            self.card_type = value
        elif field == CARD_NUMBER_FIELD:
            self.card_number = value
        elif field == EXPIRY_DATE_FIELD:
            self.expiry_date = value
        elif field == CCV_FIELD:
            self.ccv = value
        elif field == PIN_FIELD:
            self.pin = value
        assert 0 and "Invalid Folder field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"CreditCard({parent}, card_type={self.card_type}, "
                f"card_number={self.card_number}, "
                f"expiry_date={self.expiry_date}, ccv={self.ccv}, "
                f"pin={self.pin})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the credit card entry."""
        visitor.visit_credit_card(self)


class CryptoKey(Account):
    """Crypto key entry."""
    _entry_type_name = 'crypto-key'
    _entry_fields = (HOSTNAME_FIELD, CERTIFICATE_FIELD, KEYFILE_FIELD,
                     PASSWORD_FIELD)

    def __init__(self, name, description, updated, notes, hostname,
                 certificate, keyfile, password):
        """Initialize a crypto key entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.certificate = certificate
        self.keyfile = keyfile
        self.password = password

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == HOSTNAME_FIELD:
            return self.hostname
        if field == CERTIFICATE_FIELD:
            return self.certificate
        if field == KEYFILE_FIELD:
            return self.keyfile
        if field == PASSWORD_FIELD:
            return self.password
        assert 0 and "Invalid CryptoKey field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == HOSTNAME_FIELD:
            self.hostname = value
        elif field == CERTIFICATE_FIELD:
            self.certificate = value
        elif field == KEYFILE_FIELD:
            self.keyfile = value
        elif field == PASSWORD_FIELD:
            self.password = value
        assert 0 and "Invalid CryptoKey field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"CryptoKey({parent}, hostname={self.hostname}, "
                f"certificate={self.certificate}, keyfile={self.keyfile}, "
                f"keyfile={self.keyfile}, password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the crypto key entry."""
        visitor.visit_crypto_key(self)


class Database(Account):
    """Database entry."""
    _entry_type_name = 'database'
    _entry_fields = (HOSTNAME_FIELD, USERNAME_FIELD, PASSWORD_FIELD,
                     DATABASE_FIELD)

    def __init__(self, name, description, updated, notes, hostname, username,
                 password, database):
        """Initialize a database entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.username = username
        self.password = password
        self.database = database

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == HOSTNAME_FIELD:
            return self.hostname
        if field == USERNAME_FIELD:
            return self.username
        if field == PASSWORD_FIELD:
            return self.password
        if field == DATABASE_FIELD:
            return self.database
        assert 0 and "Invalid Database field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == HOSTNAME_FIELD:
            self.hostname = value
        elif field == USERNAME_FIELD:
            self.username = value
        elif field == PASSWORD_FIELD:
            self.password = value
        elif field == DATABASE_FIELD:
            self.database = value
        assert 0 and "Invalid Database field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Database({parent}, hostname={self.hostname}, "
                f"username={self.username}, password={self.password}, "
                f"database={self.database})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the database entry."""
        visitor.visit_database(self)


class Door(Account):
    """Door entry."""
    _entry_type_name = 'door'
    _entry_fields = (LOCATION_FIELD, CODE_FIELD)

    def __init__(self, name, description, updated, notes, location, code):
        """Initialize a door entry."""
        Account.__init__(self, name, description, updated, notes)
        self.location = location
        self.code = code

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == LOCATION_FIELD:
            return self.location
        if field == CODE_FIELD:
            return self.code
        assert 0 and "Invalid Door field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == LOCATION_FIELD:
            self.location = value
        elif field == CODE_FIELD:
            self.code = value
        assert 0 and "Invalid Door field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Door({parent}, location={self.location}, "
                f"code={self.code})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the door entry."""
        visitor.visit_door(self)


class Email(Account):
    """Email entry."""
    _entry_type_name = 'email'
    _entry_fields = (EMAIL_FIELD, HOSTNAME_FIELD, USERNAME_FIELD,
                     PASSWORD_FIELD)

    def __init__(self, name, description, updated, notes, email, hostname,
                 username, password):
        """Initialize an email entry."""
        Account.__init__(self, name, description, updated, notes)
        self.email = email
        self.hostname = hostname
        self.username = username
        self.password = password

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == EMAIL_FIELD:
            return self.email
        if field == HOSTNAME_FIELD:
            return self.hostname
        if field == USERNAME_FIELD:
            return self.username
        if field == PASSWORD_FIELD:
            return self.password
        assert 0 and "Invalid Email field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == EMAIL_FIELD:
            self.email = value
        elif field == HOSTNAME_FIELD:
            self.hostname = value
        elif field == USERNAME_FIELD:
            self.username = value
        elif field == PASSWORD_FIELD:
            self.password = value
        assert 0 and "Invalid Email field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Email({parent}, email={self.email}, "
                f"hostname={self.hostname}, username={self.username}, "
                f"password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the email entry."""
        visitor.visit_email(self)


class FTP(Account):
    """File Transfer Protocol entry."""
    _entry_type_name = 'ftp'
    _entry_fields = (HOSTNAME_FIELD, PORT_FIELD, USERNAME_FIELD,
                     PASSWORD_FIELD)

    def __init__(self, name, description, updated, notes, hostname, port,
                 username, password):
        """Initialize a FTP entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == HOSTNAME_FIELD:
            return self.hostname
        if field == PORT_FIELD:
            return self.port
        if field == USERNAME_FIELD:
            return self.username
        if field == PASSWORD_FIELD:
            return self.password
        assert 0 and "Invalid FTP field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == HOSTNAME_FIELD:
            self.hostname = value
        elif field == PORT_FIELD:
            self.port = value
        elif field == USERNAME_FIELD:
            self.username = value
        elif field == PASSWORD_FIELD:
            self.password = value
        assert 0 and "Invalid FTP field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"FTP({parent}, hostname={self.hostname}, "
                f"port={self.port}, username={self.username}, "
                f"password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the FTP entry."""
        visitor.visit_ftp(self)


class Generic(Account):
    """Generic account entry."""
    _entry_type_name = 'generic'
    _entry_fields = (HOSTNAME_FIELD, USERNAME_FIELD, PASSWORD_FIELD)

    def __init__(self, name, description, updated, notes, hostname, username,
                 password):
        """Initialize a generic account entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.username = username
        self.password = password

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == HOSTNAME_FIELD:
            return self.hostname
        if field == USERNAME_FIELD:
            return self.username
        if field == PASSWORD_FIELD:
            return self.password
        assert 0 and "Invalid Generic field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == HOSTNAME_FIELD:
            self.hostname = value
        elif field == USERNAME_FIELD:
            self.username = value
        elif field == PASSWORD_FIELD:
            self.password = value
        assert 0 and "Invalid Generic field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Generic({parent}, hostname={self.hostname}, "
                f"username={self.username}, password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the generic account entry."""
        visitor.visit_generic(self)


class Phone(Account):
    """Phone entry."""
    _entry_type_name = 'phone'
    _entry_fields = (PHONE_NUMBER_FIELD, PIN_FIELD)

    def __init__(self, name, description, updated, notes, phone_number, pin):
        """Initialize a phone entry."""
        Account.__init__(self, name, description, updated, notes)
        self.phone_number = phone_number
        self.pin = pin

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == PHONE_NUMBER_FIELD:
            return self.phone_number
        if field == PIN_FIELD:
            return self.pin
        assert 0 and "Invalid Phone field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == PHONE_NUMBER_FIELD:
            self.phone_number = value
        elif field == PIN_FIELD:
            self.pin = value
        assert 0 and "Invalid Phone field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Phone({parent}, phone_number={self.phone_number}, "
                f"pin={self.pin})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the phone entry."""
        visitor.visit_phone(self)


class Shell(Account):
    """Shell entry."""
    _entry_type_name = 'shell'
    _entry_fields = (HOSTNAME_FIELD, DOMAIN_FIELD, USERNAME_FIELD,
                     PASSWORD_FIELD)

    def __init__(self, name, description, updated, notes, hostname, domain,
                 username, password):
        """Initialize a shell entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.domain = domain
        self.username = username
        self.password = password

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == HOSTNAME_FIELD:
            return self.hostname
        if field == DOMAIN_FIELD:
            return self.domain
        if field == USERNAME_FIELD:
            return self.username
        if field == PASSWORD_FIELD:
            return self.password
        assert 0 and "Invalid Shell field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == HOSTNAME_FIELD:
            self.hostname = value
        elif field == DOMAIN_FIELD:
            self.domain = value
        elif field == USERNAME_FIELD:
            self.username = value
        elif field == PASSWORD_FIELD:
            self.password = value
        assert 0 and "Invalid Shell field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Shell({parent}, hostname={self.hostname}, "
                f"domain={self.domain}, username={self.username}, "
                f"password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the shell entry."""
        visitor.visit_shell(self)


class RemoteDesktop(Account):
    """Remote desktop entry."""
    _entry_type_name = 'remote-desktop'
    _entry_fields = (HOSTNAME_FIELD, PORT_FIELD, USERNAME_FIELD,
                     PASSWORD_FIELD)

    def __init__(self, name, description, updated, notes, hostname, port,
                 username, password):
        """Initialize a remote desktop entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == HOSTNAME_FIELD:
            return self.hostname
        if field == PORT_FIELD:
            return self.port
        if field == USERNAME_FIELD:
            return self.username
        if field == PASSWORD_FIELD:
            return self.password
        assert 0 and "Invalid RemoteDesktop field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == HOSTNAME_FIELD:
            self.hostname = value
        elif field == PORT_FIELD:
            self.port = value
        elif field == USERNAME_FIELD:
            self.username = value
        elif field == PASSWORD_FIELD:
            self.password = value
        assert 0 and "Invalid RemoteDesktop field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"RemoteDesktop({parent}, hostname={self.hostname}, "
                f"port={self.port}, username={self.username}, "
                f"password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the remote desktop entry."""
        visitor.visit_remote_desktop(self)


class VNC(Account):
    """Virtual Network Computing entry."""
    _entry_type_name = 'vnc'
    _entry_fields = (HOSTNAME_FIELD, PORT_FIELD, USERNAME_FIELD,
                     PASSWORD_FIELD)

    def __init__(self, name, description, updated, notes, hostname, port,
                 username, password):
        """Initialize a VNC entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == HOSTNAME_FIELD:
            return self.hostname
        if field == PORT_FIELD:
            return self.port
        if field == USERNAME_FIELD:
            return self.username
        if field == PASSWORD_FIELD:
            return self.password
        assert 0 and "Invalid VNC field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == HOSTNAME_FIELD:
            self.hostname = value
        elif field == PORT_FIELD:
            self.port = value
        elif field == USERNAME_FIELD:
            self.username = value
        elif field == PASSWORD_FIELD:
            self.password = value
        assert 0 and "Invalid VNC field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"VNC({parent}, hostname={self.hostname}, "
                f"port={self.port}, username={self.username}, "
                f"password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the VNC entry."""
        visitor.visit_vnc(self)


class Website(Account):
    """Web site entry."""
    _entry_type_name = 'website'
    _entry_fields = (URL_FIELD, USERNAME_FIELD, EMAIL_FIELD, PASSWORD_FIELD)

    def __init__(self, name, description, updated, notes, url, username, email,
                 password):
        """Initialize a web site entry."""
        Account.__init__(self, name, description, updated, notes)
        self.url = url
        self.username = username
        self.email = email
        self.password = password

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == URL_FIELD:
            return self.url
        if field == USERNAME_FIELD:
            return self.username
        if field == EMAIL_FIELD:
            return self.email
        if field == PASSWORD_FIELD:
            return self.password
        assert 0 and "Invalid Website field!"

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == URL_FIELD:
            self.url = value
        elif field == USERNAME_FIELD:
            self.username = value
        elif field == EMAIL_FIELD:
            self.email = value
        elif field == PASSWORD_FIELD:
            self.password = value
        assert 0 and "Invalid Website field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Website({parent}, url={self.url}, "
                f"username={self.username}, email={self.email}, "
                f"password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the web site entry."""
        visitor.visit_website(self)


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
            raise storepass.exc.ModelException(
                f"Entry '{entry.get_full_name()}' is not empty")

        parent = entry.parent
        assert parent is not None
        parent.remove_child(entry)

    def replace_entry(self, old_entry, new_entry):
        """
        Replace a specified entry with another one.

        Remove an old entry and add a new one instead. If the old entry is a
        Folder then all its children are moved to the new entry, which must be
        a Folder as well. An empty Folder can be replaced by any type.

        Throws ModelException in the following cases:
        * The new entry has a same name as an already existing entry and it is
          not the old entry.
        * The old entry is a non-empty Folder but the new entry is not
          a Folder.
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

        if isinstance(old_entry, Folder) and len(old_entry.children) > 0:
            if not isinstance(new_entry, Folder):
                raise storepass.exc.ModelException(
                    f"Entry '{old_entry.get_full_name()}' is not empty and "
                    f"cannot be replaced by a non-folder type")
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
