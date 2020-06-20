# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Tests for the storage module."""

import datetime
import os

import storepass.exc
import storepass.model
import storepass.storage
from . import util

DEFAULT_PASSWORD = 'qwerty'


class TestStorage(util.StorePassTestCase):
    """Tests for the storage module."""
    def test_read_plain(self):
        """Check that the plain reader can output raw database content."""
        util.write_password_db(self.dbname, DEFAULT_PASSWORD, 'RAW CONTENT')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        data = storage.read_plain()
        self.assertEqual(data, 'RAW CONTENT')

    def test_read_invalid_file(self):
        """Check that an unreadable file is sensibly rejected."""
        storage = storepass.storage.Storage(os.getcwd(), DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertRegex(str(cm.exception), r"\[Errno 21\] Is a directory:")

    def test_read_header_size_min(self):
        """Check rejection of an incomplete header (minimum case)."""
        util.write_file(self.dbname, b'')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "File header is incomplete, expected '12' bytes but found '0'")

    def test_read_header_size_max(self):
        """Check rejection of an incomplete header (maximum case)."""
        util.write_file(self.dbname,
                        b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "File header is incomplete, expected '12' bytes but found '11'")

    def test_read_salt_size_min(self):
        """Check rejection of incomplete salt data (minimum case)."""
        util.write_file(self.dbname,
                        b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Salt record is incomplete, expected '8' bytes but found '0'")

    def test_read_salt_size_max(self):
        """Check rejection of incomplete salt data (maximum case)."""
        util.write_file(
            self.dbname,
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Salt record is incomplete, expected '8' bytes but found '7'")

    def test_read_init_size_min(self):
        """Check rejection of an incomplete init vector (minimum case)."""
        util.write_file(
            self.dbname,
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Initialization vector is incomplete, expected '16' bytes but "
            "found '0'")

    def test_read_init_size_max(self):
        """Check rejection of an incomplete init vector (maximum case)."""
        util.write_file(
            self.dbname,
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Initialization vector is incomplete, expected '16' bytes but "
            "found '15'")

    def test_read_encrypted_alignment(self):
        """Check rejection of misaligned encrypted data."""
        util.write_file(
            self.dbname,
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22\x23\x24')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Data record with size of '1' bytes is not 16-byte aligned")

    def test_read_header_magic(self):
        """Check rejection of an invalid magic number in a file header."""
        util.write_file(
            self.dbname,
            b'\xff\xff\xff\xff\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22\x23')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Invalid magic number, expected b'rvl\\x00' but found "
            "b'\\xff\\xff\\xff\\xff'")

    def test_read_header_version(self):
        """Check rejection of an unsupported verion number in a file header."""
        util.write_file(
            self.dbname,
            b'rvl\x00\xff\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22\x23')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Unsupported envelope data version, expected b'2' but found "
            "b'\\xff'")

    def test_read_header_padding(self):
        """Check rejection of a wrong pad at bytes [5:6) in a file header."""
        util.write_file(
            self.dbname,
            b'rvl\x00\x02\xff\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22\x23')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Non-zero header padding at bytes [5:6), found b'\\xff'")

    def test_read_header_padding2(self):
        """Check rejection of a wrong pad at bytes [9:12) in a file header."""
        util.write_file(
            self.dbname,
            b'rvl\x00\x02\x00\x06\x07\x08\xff\xff\xff\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22\x23')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Non-zero header padding at bytes [9:12), found b'\\xff\\xff\\xff'"
        )

    def test_read_password(self):
        """Check rejection of a wrong database password."""
        util.write_password_db(self.dbname, 'a', 'RAW CONTENT')

        storage = storepass.storage.Storage(self.dbname, 'b')
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception), "Incorrect password")

    def test_read_no_compressed_data(self):
        """Check rejection of compressed data with zero size."""
        util.write_password_db(self.dbname,
                               DEFAULT_PASSWORD,
                               '',
                               compress=False)

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_plain()
        self.assertEqual(str(cm.exception), "Compressed data have zero size")

    def test_read_wrong_padding_length(self):
        """Check rejection of a wrong padding length for compressed data."""
        util.write_password_db(
            self.dbname,
            DEFAULT_PASSWORD,
            '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x11',
            compress=False)

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Compressed data have incorrect padding, length '17' is bigger "
            "than '16' bytes")

    def test_read_wrong_padding_bytes(self):
        """Check rejection of a wrong padding content for compressed data."""
        util.write_password_db(
            self.dbname,
            DEFAULT_PASSWORD,
            '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x02',
            compress=False)

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Compressed data have incorrect padding, expected b'\\x02\\x02' "
            "but found b'\\x0e\\x02'")

    def test_read_wrong_compression(self):
        """Check rejection of wrongly compressed data."""
        util.write_password_db(
            self.dbname,
            DEFAULT_PASSWORD,
            '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x01',
            compress=False)

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Error -3 while decompressing data: incorrect header check")

    def test_read_wrong_utf8(self):
        """Check rejection of wrongly encoded data."""
        util.write_password_db(self.dbname, DEFAULT_PASSWORD, b'\xff')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Error decoding payload: 'utf-8' codec can't decode byte 0xff in "
            "position 0: invalid start byte")

    def test_read_wrong_xml(self):
        """Check rejection of not well-formed XML."""
        util.write_password_db(self.dbname, DEFAULT_PASSWORD, '</xml>')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception),
            "Error parsing XML payload: not well-formed (invalid token): "
            "line 1, column 1")

    def test_read_wrong_root_element(self):
        """Check rejection of a wrong root element."""
        util.write_password_db(self.dbname, DEFAULT_PASSWORD, '<data/>')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception),
            "Invalid root element '/data', expected 'revelationdata'")

    def test_read_wrong_root_attribute(self):
        """Check rejection of a wrong <revelationdata> attribute."""
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            '<revelationdata invalid-attr="invalid-value"></revelationdata>')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception),
            "Element '/revelationdata' has unrecognized attribute "
            "'invalid-attr'")

    def test_read_wrong_root_dataversion(self):
        """Check rejection of an unexpected 'dataversion' attribute."""
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            '<revelationdata dataversion="2"></revelationdata>')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception),
            "Unsupported XML data version, expected attribute "
            "'/revelationdata/@dataversion' to be '1' but found '2'")

    def test_read_wrong_entry_attribute(self):
        """Check rejection of a wrong <entry> attribute."""
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry invalid-attr="invalid-value">
                \t</entry>
                </revelationdata>
                '''))

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception),
            "Element '/revelationdata/entry[1]' has unrecognized attribute "
            "'invalid-attr'")

    def test_read_folder_entry(self):
        """Check parsing of a single folder entry."""
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t</entry>
                </revelationdata>
                '''))

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        root = storage.read_tree()

        self.assertTrue(isinstance(root, storepass.model.Root))
        self.assertEqual(len(root.children), 1)

        child_0 = root.children[0]
        self.assertIs(type(child_0), storepass.model.Folder)
        self.assertEqual(child_0.name, "E1 name")
        self.assertEqual(child_0.description, "E1 description")
        self.assertEqual(
            child_0.updated,
            datetime.datetime.fromtimestamp(1546300800, datetime.timezone.utc))
        self.assertEqual(child_0.children, [])

    def test_read_wrong_folder_entry_property(self):
        """Check rejection of a wrong property for <entry type="folder">."""
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<invalid-property>invalid-value</invalid-property>
                \t</entry>
                </revelationdata>
                '''))

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception), "Unrecognized sub-folder element "
            "'/revelationdata/entry[1]/invalid-property'")

    def test_read_wrong_name_attribute(self):
        """Check rejection of a wrong <name> attribute."""
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<name invalid-attribute="invalid-value">E1</name>
                \t</entry>
                </revelationdata>
                '''))

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception),
            "Element '/revelationdata/entry[1]/name' has unrecognized "
            "attribute 'invalid-attribute'")

    def test_read_wrong_updated_value(self):
        """Check rejection of invalid <updated> values."""
        # Empty value is rejected.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<updated></updated>
                \t</entry>
                </revelationdata>
                '''))

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception),
            "Element '/revelationdata/entry[1]/updated' has invalid value '': "
            "string is empty")

        # Non-digit value is rejected.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<updated>invalid-value</updated>
                \t</entry>
                </revelationdata>
                '''))

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception),
            "Element '/revelationdata/entry[1]/updated' has invalid value "
            "'invalid-value': string contains a non-digit character")

        # Negative value is rejected.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<updated>-1</updated>
                \t</entry>
                </revelationdata>
                '''))

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception),
            "Element '/revelationdata/entry[1]/updated' has invalid value "
            "'-1': string contains a non-digit character")

        # Overflow value is rejected.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<updated>100020003000400050006000700090000000</updated>
                \t</entry>
                </revelationdata>
                '''))

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception),
            "Element '/revelationdata/entry[1]/updated' has invalid value "
            "'100020003000400050006000700090000000': timestamp out of range "
            "for platform time_t")

    def test_read_generic_entry(self):
        """Check parsing of a single generic entry."""
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="generic">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-password">E1 password</field>
                \t</entry>
                </revelationdata>
                '''))

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        root = storage.read_tree()

        self.assertTrue(isinstance(root, storepass.model.Root))
        self.assertEqual(len(root.children), 1)

        child_0 = root.children[0]
        self.assertIs(type(child_0), storepass.model.Generic)
        self.assertEqual(child_0.name, "E1 name")
        self.assertEqual(child_0.description, "E1 description")
        self.assertEqual(
            child_0.updated,
            datetime.datetime.fromtimestamp(1546300800, datetime.timezone.utc))
        self.assertEqual(child_0.notes, "E1 notes")
        self.assertEqual(child_0.hostname, "E1 hostname")
        self.assertEqual(child_0.username, "E1 username")
        self.assertEqual(child_0.password, "E1 password")

    def test_read_wrong_generic_entry_property(self):
        """Check rejection of a wrong property for <entry type="generic">."""
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="generic">
                \t\t<invalid-property>invalid-value</invalid-property>
                \t</entry>
                </revelationdata>
                '''))

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception), "Unrecognized sub-generic element "
            "'/revelationdata/entry[1]/invalid-property'")

    def test_read_wrong_generic_field_attribute(self):
        """Check rejection of a wrong generic-entry <field> attribute."""
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="generic">
                \t\t<field invalid-attribute="invalid-value">E1 field</field>
                \t</entry>
                </revelationdata>
                '''))

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception),
            "Element '/revelationdata/entry[1]/field' has unrecognized "
            "attribute 'invalid-attribute'")

    def test_read_wrong_generic_field_id(self):
        """Check rejection of a wrong generic-entry <field> id attribute."""
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="generic">
                \t\t<field id="invalid-id">E1 field</field>
                \t</entry>
                </revelationdata>
                '''))

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_tree()
        self.assertEqual(
            str(cm.exception),
            "Attribute '/revelationdata/entry[1]/field/@id' has "
            "unrecognized value 'invalid-id', expected 'generic-hostname', "
            "'generic-username' or 'generic-password'")

    def test_write_plain(self):
        """Check that the plain writer can save raw database content."""
        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        storage.write_plain('RAW CONTENT')

        data = util.read_password_db(self.dbname, DEFAULT_PASSWORD, self)
        self.assertEqual(data, 'RAW CONTENT')

    def test_write_invalid_file(self):
        """Check that an unwritable file is sensibly rejected."""
        storage = storepass.storage.Storage(os.getcwd(), DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageWriteException) as cm:
            storage.write_plain('')
        self.assertRegex(str(cm.exception), r"\[Errno 21\] Is a directory:")

    def test_write_generic_entry(self):
        """Check output of a single generic entry."""
        generic = storepass.model.Generic(
            "E1 name", "E1 description",
            datetime.datetime.fromtimestamp(1546300800, datetime.timezone.utc),
            "E1 notes", "E1 hostname", "E1 username", "E1 password")
        root = storepass.model.Root([generic])

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        storage.write_tree(root)

        data = util.read_password_db(self.dbname, DEFAULT_PASSWORD, self)
        self.assertEqual(
            data,
            util.dedent('''\
                <?xml version='1.0' encoding='UTF-8'?>
                <revelationdata dataversion="1">
                \t<entry type="generic">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-password">E1 password</field>
                \t</entry>
                </revelationdata>
                '''))
