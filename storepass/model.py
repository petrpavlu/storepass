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
import logging

import storepass.exc
import storepass.util

_logger = logging.getLogger(__name__)


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
            if char not in ('\\', '/'):
                raise storepass.exc.ModelException(
                    f"Entry name '{path_string}' contains invalid escape "
                    f"sequence '\\{char}'")
            element += char
            state = _State.NORMAL
    res.append(element)

    if state == _State.ESCAPE:
        raise storepass.exc.ModelException(
            f"Entry name '{path_string}' has an incomplete escape sequence at "
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
    def __init__(self, name, label, storage_id, is_protected=False):
        """Initialize an entry field."""
        self._name = name
        self._label = label
        self._storage_id = storage_id
        self._is_protected = is_protected

    @property
    def name(self):
        """Obtain a name of the field."""
        return self._name

    @property
    def label(self):
        """Obtain the field's label."""
        return self._label

    @property
    def storage_id(self):
        """Obtain the field's storage ID."""
        return self._storage_id

    @property
    def is_protected(self):
        """Obtain whether the field is protected, e.g. it is a password."""
        return self._is_protected


CARD_NUMBER_FIELD = Field('card-number', "Card number",
                          'creditcard-cardnumber')
CARD_TYPE_FIELD = Field('card-type', "Card type", 'creditcard-cardtype')
CCV_FIELD = Field('ccv', "CCV", 'creditcard-ccv')
CERTIFICATE_FIELD = Field('certificate', "Certificate", 'generic-certificate')
CODE_FIELD = Field('code', "Code", 'generic-code')
DATABASE_FIELD = Field('database', "Database", 'generic-database')
DOMAIN_FIELD = Field('domain', "Domain", 'generic-domain')
EMAIL_FIELD = Field('email', "Email", 'generic-email')
EXPIRY_DATE_FIELD = Field('expiry-date', "Expiry date",
                          'creditcard-expirydate')
HOSTNAME_FIELD = Field('hostname', "Hostname", 'generic-hostname')
KEYFILE_FIELD = Field('keyfile', "Keyfile", 'generic-keyfile')
LOCATION_FIELD = Field('location', "Location", 'generic-location')
PASSWORD_FIELD = Field('password',
                       "Password",
                       'generic-password',
                       is_protected=True)
PHONE_NUMBER_FIELD = Field('phone-number', "Phone number", 'phone-phonenumber')
PIN_FIELD = Field('pin', "PIN", 'generic-pin')
PORT_FIELD = Field('port', "Port", 'generic-port')
URL_FIELD = Field('url', "URL", 'generic-url')
USERNAME_FIELD = Field('username', "Username", 'generic-username')

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

    def accept_children(self, visitor, parent_data):
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
            self.accept_children(visitor, parent_data)


class Entry:
    """Database entry base class."""

    _entry_type_name = 'entry'
    _entry_label = "Entry"
    _entry_fields = ()
    _storage_id = 'entry'

    @storepass.util.classproperty
    def entry_type_name(cls):  # pylint: disable=no-self-argument
        """Obtain the entry type name."""
        return cls._entry_type_name

    @storepass.util.classproperty
    def entry_label(cls):  # pylint: disable=no-self-argument
        """Obtain the entry's label."""
        return cls._entry_label

    @storepass.util.classproperty
    def entry_fields(cls):  # pylint: disable=no-self-argument
        """Obtain fields that are valid for the entry."""
        return cls._entry_fields

    @storepass.util.classproperty
    def storage_id(cls):  # pylint: disable=no-self-argument
        """Obtain entry's storage ID."""
        return cls._storage_id

    class _PropertyProxy:
        """Proxy to access an entry property via a field."""
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
    def from_proxy(cls, _name, _description, _updated, _notes, _properties):
        """Create an entry via the properties specification."""
        assert 0 and "Unimplemented method from_properties()!"

    @property
    def parent(self):
        """Obtain the parent container."""
        return self._parent

    @property
    def name(self):
        """Obtain a name of the entry."""
        return self._name

    def _get_field(self, _field):
        """Get a value of a specified field."""
        assert 0 and "Unimplemented method _get_field()!"

    def _set_field(self, _field, _value):
        """Set a new value of a specified field."""
        assert 0 and "Unimplemented method _set_field()!"

    def update_fields(self, properties):
        """Update entry's fields from specified property values."""
        for field, value in properties.items():
            self._set_field(field, value)

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
    _entry_label = "Folder"
    _entry_fields = ()
    _storage_id = 'folder'

    def __init__(self, name, description, updated, notes, children):
        """Initialize a password folder."""
        Container.__init__(self, children)
        Entry.__init__(self, name, description, updated, notes)

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create a folder via the properties specification."""
        res = Folder(name, description, updated, notes, [])
        res.update_fields(properties)
        return res

    def _get_field(self, _field):
        """Get a value of a specified field."""
        assert 0 and "Invalid Folder field!"

    def _set_field(self, _field, _value):
        """Set a new value of a specified field."""
        assert 0 and "Invalid Folder field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        res = indent + f"Folder({parent}):"
        for child in self._children:
            res += "\n" + child.__str__(indent + "  ")
        return res

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

    def accept(self, visitor, single=False):
        """
        Visit the folder and its children.

        Call a given visitor to process the folder and its children. If single
        is set to False then only the folder object is visited.
        """
        if hasattr(visitor, 'visit_folder'):
            parent_data = visitor.visit_folder(self)
        elif hasattr(visitor, 'visit_entry'):
            parent_data = visitor.visit_entry(self)
        else:
            assert 0 and "Unimplemented visitor method!"
        if not single:
            self.accept_children(visitor, parent_data)


class Account(Entry):
    """Account entry base class."""
    def __init__(self, name, description, updated, notes):
        """Initialize an abstract account entry."""
        Entry.__init__(self, name, description, updated, notes)

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the account entry."""
        if hasattr(visitor, 'visit_account'):
            visitor.visit_account(self)
        elif hasattr(visitor, 'visit_entry'):
            visitor.visit_entry(self)
        else:
            assert 0 and "Unimplemented visitor method!"


class CreditCard(Account):
    """Credit card entry."""
    _entry_type_name = 'credit-card'
    _entry_label = "Credit card"
    _entry_fields = (CARD_TYPE_FIELD, CARD_NUMBER_FIELD, EXPIRY_DATE_FIELD,
                     CCV_FIELD, PIN_FIELD)
    _storage_id = 'creditcard'

    def __init__(self, name, description, updated, notes, card_type,
                 card_number, expiry_date, ccv, pin):
        """Initialize a credit card entry."""
        Account.__init__(self, name, description, updated, notes)
        self.card_type = card_type
        self.card_number = card_number
        self.expiry_date = expiry_date
        self.ccv = ccv
        self.pin = pin

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create a credit card entry via the properties specification."""
        res = CreditCard(name, description, updated, notes, None, None, None,
                         None, None)
        res.update_fields(properties)
        return res

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
        return None

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
        else:
            assert 0 and "Invalid Folder field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"CreditCard({parent}, card_type={self.card_type}, "
                f"card_number={self.card_number}, "
                f"expiry_date={self.expiry_date}, ccv={self.ccv}, "
                f"pin={self.pin})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the credit card entry."""
        if hasattr(visitor, 'visit_credit_card'):
            visitor.visit_credit_card(self)
        else:
            super().accept(visitor, single)


class CryptoKey(Account):
    """Crypto key entry."""
    _entry_type_name = 'crypto-key'
    _entry_label = "Crypto key"
    _entry_fields = (HOSTNAME_FIELD, CERTIFICATE_FIELD, KEYFILE_FIELD,
                     PASSWORD_FIELD)
    _storage_id = 'cryptokey'

    def __init__(self, name, description, updated, notes, hostname,
                 certificate, keyfile, password):
        """Initialize a crypto key entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.certificate = certificate
        self.keyfile = keyfile
        self.password = password

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create a crypto key entry via the properties specification."""
        res = CryptoKey(name, description, updated, notes, None, None, None,
                        None)
        res.update_fields(properties)
        return res

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
        return None

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
        else:
            assert 0 and "Invalid CryptoKey field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"CryptoKey({parent}, hostname={self.hostname}, "
                f"certificate={self.certificate}, keyfile={self.keyfile}, "
                f"keyfile={self.keyfile}, password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the crypto key entry."""
        if hasattr(visitor, 'visit_crypto_key'):
            visitor.visit_crypto_key(self)
        else:
            super().accept(visitor, single)


class Database(Account):
    """Database entry."""
    _entry_type_name = 'database'
    _entry_label = "Database"
    _entry_fields = (HOSTNAME_FIELD, USERNAME_FIELD, PASSWORD_FIELD,
                     DATABASE_FIELD)
    _storage_id = 'database'

    def __init__(self, name, description, updated, notes, hostname, username,
                 password, database):
        """Initialize a database entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.username = username
        self.password = password
        self.database = database

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create a database entry via the properties specification."""
        res = Database(name, description, updated, notes, None, None, None,
                       None)
        res.update_fields(properties)
        return res

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
        return None

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
        else:
            assert 0 and "Invalid Database field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Database({parent}, hostname={self.hostname}, "
                f"username={self.username}, password={self.password}, "
                f"database={self.database})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the database entry."""
        if hasattr(visitor, 'visit_database'):
            visitor.visit_database(self)
        else:
            super().accept(visitor, single)


class Door(Account):
    """Door entry."""
    _entry_type_name = 'door'
    _entry_label = "Door"
    _entry_fields = (LOCATION_FIELD, CODE_FIELD)
    _storage_id = 'door'

    def __init__(self, name, description, updated, notes, location, code):
        """Initialize a door entry."""
        Account.__init__(self, name, description, updated, notes)
        self.location = location
        self.code = code

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create a door entry via the properties specification."""
        res = Door(name, description, updated, notes, None, None)
        res.update_fields(properties)
        return res

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == LOCATION_FIELD:
            return self.location
        if field == CODE_FIELD:
            return self.code
        assert 0 and "Invalid Door field!"
        return None

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == LOCATION_FIELD:
            self.location = value
        elif field == CODE_FIELD:
            self.code = value
        else:
            assert 0 and "Invalid Door field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Door({parent}, location={self.location}, "
                f"code={self.code})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the door entry."""
        if hasattr(visitor, 'visit_door'):
            visitor.visit_door(self)
        else:
            super().accept(visitor, single)


class Email(Account):
    """Email entry."""
    _entry_type_name = 'email'
    _entry_label = "Email"
    _entry_fields = (EMAIL_FIELD, HOSTNAME_FIELD, USERNAME_FIELD,
                     PASSWORD_FIELD)
    _storage_id = 'email'

    def __init__(self, name, description, updated, notes, email, hostname,
                 username, password):
        """Initialize an email entry."""
        Account.__init__(self, name, description, updated, notes)
        self.email = email
        self.hostname = hostname
        self.username = username
        self.password = password

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create an email entry via the properties specification."""
        res = Email(name, description, updated, notes, None, None, None, None)
        res.update_fields(properties)
        return res

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
        return None

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
        else:
            assert 0 and "Invalid Email field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Email({parent}, email={self.email}, "
                f"hostname={self.hostname}, username={self.username}, "
                f"password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the email entry."""
        if hasattr(visitor, 'visit_email'):
            visitor.visit_email(self)
        else:
            super().accept(visitor, single)


class FTP(Account):
    """File Transfer Protocol entry."""
    _entry_type_name = 'ftp'
    _entry_label = "FTP"
    _entry_fields = (HOSTNAME_FIELD, PORT_FIELD, USERNAME_FIELD,
                     PASSWORD_FIELD)
    _storage_id = 'ftp'

    def __init__(self, name, description, updated, notes, hostname, port,
                 username, password):
        """Initialize a FTP entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create a FTP entry via the properties specification."""
        res = FTP(name, description, updated, notes, None, None, None, None)
        res.update_fields(properties)
        return res

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
        return None

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
        else:
            assert 0 and "Invalid FTP field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"FTP({parent}, hostname={self.hostname}, "
                f"port={self.port}, username={self.username}, "
                f"password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the FTP entry."""
        if hasattr(visitor, 'visit_ftp'):
            visitor.visit_ftp(self)
        else:
            super().accept(visitor, single)


class Generic(Account):
    """Generic account entry."""
    _entry_type_name = 'generic'
    _entry_label = "Generic"
    _entry_fields = (HOSTNAME_FIELD, USERNAME_FIELD, PASSWORD_FIELD)
    _storage_id = 'generic'

    def __init__(self, name, description, updated, notes, hostname, username,
                 password):
        """Initialize a generic account entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.username = username
        self.password = password

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create a generic account entry via the properties specification."""
        res = Generic(name, description, updated, notes, None, None, None)
        res.update_fields(properties)
        return res

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == HOSTNAME_FIELD:
            return self.hostname
        if field == USERNAME_FIELD:
            return self.username
        if field == PASSWORD_FIELD:
            return self.password
        assert 0 and "Invalid Generic field!"
        return None

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == HOSTNAME_FIELD:
            self.hostname = value
        elif field == USERNAME_FIELD:
            self.username = value
        elif field == PASSWORD_FIELD:
            self.password = value
        else:
            assert 0 and "Invalid Generic field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Generic({parent}, hostname={self.hostname}, "
                f"username={self.username}, password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the generic account entry."""
        if hasattr(visitor, 'visit_generic'):
            visitor.visit_generic(self)
        else:
            super().accept(visitor, single)


class Phone(Account):
    """Phone entry."""
    _entry_type_name = 'phone'
    _entry_label = "Phone"
    _entry_fields = (PHONE_NUMBER_FIELD, PIN_FIELD)
    _storage_id = 'phone'

    def __init__(self, name, description, updated, notes, phone_number, pin):
        """Initialize a phone entry."""
        Account.__init__(self, name, description, updated, notes)
        self.phone_number = phone_number
        self.pin = pin

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create a phone entry via the properties specification."""
        res = Phone(name, description, updated, notes, None, None)
        res.update_fields(properties)
        return res

    def _get_field(self, field):
        """Get a value of a specified field."""
        if field == PHONE_NUMBER_FIELD:
            return self.phone_number
        if field == PIN_FIELD:
            return self.pin
        assert 0 and "Invalid Phone field!"
        return None

    def _set_field(self, field, value):
        """Set a new value of a specified field."""
        if field == PHONE_NUMBER_FIELD:
            self.phone_number = value
        elif field == PIN_FIELD:
            self.pin = value
        else:
            assert 0 and "Invalid Phone field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Phone({parent}, phone_number={self.phone_number}, "
                f"pin={self.pin})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the phone entry."""
        if hasattr(visitor, 'visit_phone'):
            visitor.visit_phone(self)
        else:
            super().accept(visitor, single)


class Shell(Account):
    """Shell entry."""
    _entry_type_name = 'shell'
    _entry_label = "Shell"
    _entry_fields = (HOSTNAME_FIELD, DOMAIN_FIELD, USERNAME_FIELD,
                     PASSWORD_FIELD)
    _storage_id = 'shell'

    def __init__(self, name, description, updated, notes, hostname, domain,
                 username, password):
        """Initialize a shell entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.domain = domain
        self.username = username
        self.password = password

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create a shell entry via the properties specification."""
        res = Shell(name, description, updated, notes, None, None, None, None)
        res.update_fields(properties)
        return res

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
        return None

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
        else:
            assert 0 and "Invalid Shell field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Shell({parent}, hostname={self.hostname}, "
                f"domain={self.domain}, username={self.username}, "
                f"password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the shell entry."""
        if hasattr(visitor, 'visit_shell'):
            visitor.visit_shell(self)
        else:
            super().accept(visitor, single)


class RemoteDesktop(Account):
    """Remote desktop entry."""
    _entry_type_name = 'remote-desktop'
    _entry_label = "Remote desktop"
    _entry_fields = (HOSTNAME_FIELD, PORT_FIELD, USERNAME_FIELD,
                     PASSWORD_FIELD)
    _storage_id = 'remotedesktop'

    def __init__(self, name, description, updated, notes, hostname, port,
                 username, password):
        """Initialize a remote desktop entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create a remote desktop entry via the properties specification."""
        res = RemoteDesktop(name, description, updated, notes, None, None,
                            None, None)
        res.update_fields(properties)
        return res

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
        return None

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
        else:
            assert 0 and "Invalid RemoteDesktop field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"RemoteDesktop({parent}, hostname={self.hostname}, "
                f"port={self.port}, username={self.username}, "
                f"password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the remote desktop entry."""
        if hasattr(visitor, 'visit_remote_desktop'):
            visitor.visit_remote_desktop(self)
        else:
            super().accept(visitor, single)


class VNC(Account):
    """Virtual Network Computing entry."""
    _entry_type_name = 'vnc'
    _entry_label = "VNC"
    _entry_fields = (HOSTNAME_FIELD, PORT_FIELD, USERNAME_FIELD,
                     PASSWORD_FIELD)
    _storage_id = 'vnc'

    def __init__(self, name, description, updated, notes, hostname, port,
                 username, password):
        """Initialize a VNC entry."""
        Account.__init__(self, name, description, updated, notes)
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create a VNC entry via the properties specification."""
        res = VNC(name, description, updated, notes, None, None, None, None)
        res.update_fields(properties)
        return res

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
        return None

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
        else:
            assert 0 and "Invalid VNC field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"VNC({parent}, hostname={self.hostname}, "
                f"port={self.port}, username={self.username}, "
                f"password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the VNC entry."""
        if hasattr(visitor, 'visit_vnc'):
            visitor.visit_vnc(self)
        else:
            super().accept(visitor, single)


class Website(Account):
    """Web site entry."""
    _entry_type_name = 'website'
    _entry_label = "Website"
    _entry_fields = (URL_FIELD, USERNAME_FIELD, EMAIL_FIELD, PASSWORD_FIELD)
    _storage_id = 'website'

    def __init__(self, name, description, updated, notes, url, username, email,
                 password):
        """Initialize a web site entry."""
        Account.__init__(self, name, description, updated, notes)
        self.url = url
        self.username = username
        self.email = email
        self.password = password

    @classmethod
    def from_proxy(cls, name, description, updated, notes, properties):
        """Create a website entry via the properties specification."""
        res = Website(name, description, updated, notes, None, None, None,
                      None)
        res.update_fields(properties)
        return res

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
        return None

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
        else:
            assert 0 and "Invalid Website field!"

    def __str__(self, indent=""):
        parent = super().inline_str()
        return (indent + f"Website({parent}, url={self.url}, "
                f"username={self.username}, email={self.email}, "
                f"password={self.password})")

    def accept(self, visitor, single=False):  # pylint: disable=unused-argument
        """Visit the web site entry."""
        if hasattr(visitor, 'visit_website'):
            visitor.visit_website(self)
        else:
            super().accept(visitor, single)


ENTRY_TYPES = (
    Folder,
    CreditCard,
    CryptoKey,
    Database,
    Door,
    Email,
    FTP,
    Generic,
    Phone,
    Shell,
    RemoteDesktop,
    VNC,
    Website,
)


class Model:
    """Database model."""
    def __init__(self, root=Root([])):
        """Initialize a database model."""
        self._root = root

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
        _logger.debug("Adding entry '%s' under '%s'", new_entry.name,
                      parent.get_full_name())
        if not parent.add_child(new_entry):
            parent_path_spec = parent.get_path()
            path_string = path_spec_to_string(parent_path_spec +
                                              [new_entry.name])
            raise storepass.exc.ModelException(
                f"Entry '{path_string}' already exists")

    def move_entry(self, entry, new_parent):
        """
        Move a previously added entry under a new parent.

        Re-parent an entry under another container.

        Throws ModelException in the following cases:
        * An entry with the same name already exists.
        * The entry is moved under itself.
        """
        _logger.debug("Moving entry '%s' under '%s'", entry.get_full_name(),
                      new_parent.get_full_name())

        ancestor = new_parent
        while not isinstance(ancestor, Root):
            if ancestor == entry:
                raise storepass.exc.ModelException(
                    f"Entry '{entry.get_full_name()}' cannot be moved under "
                    f"'{new_parent.get_full_name()}' because it constitutes "
                    f"a path to the latter")
            ancestor = ancestor.parent

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
        _logger.debug("Removing entry '%s'", entry.get_full_name())
        if isinstance(entry, Container) and len(entry.children) > 0:
            raise storepass.exc.ModelException(
                f"Entry '{entry.get_full_name()}' is non-empty and cannot be "
                f"removed")

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
        _logger.debug("Replacing entry '%s' with '%s'",
                      old_entry.get_full_name(), new_entry.name)
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
                    f"Entry '{old_entry.get_full_name()}' is non-empty and "
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
