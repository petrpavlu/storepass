# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import datetime
import os

import storepass.exc
import storepass.model
import storepass.storage
from . import helpers

DEFAULT_PASSWORD = 'qwerty'


class TestStorage(helpers.StorePassTestCase):
    def test_read_plain(self):
        """Check that the plain reader can output raw database content."""

        helpers.write_password_db(self.dbname, DEFAULT_PASSWORD, 'RAW CONTENT')

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
        """
        Check that a file with an incomplete header is sensibly rejected
        (minimum corner case).
        """

        helpers.write_file(self.dbname, b'')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "File header is incomplete, expected '12' bytes but found '0'")

    def test_read_header_size_max(self):
        """
        Check that a file with an incomplete header is sensibly rejected
        (maximum corner case).
        """

        helpers.write_file(self.dbname,
                           b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "File header is incomplete, expected '12' bytes but found '11'")

    def test_read_salt_size_min(self):
        """
        Check that a file with an incomplete salt data is sensibly rejected
        (minimum corner case).
        """

        helpers.write_file(
            self.dbname, b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Salt record is incomplete, expected '8' bytes but found '0'")

    def test_read_salt_size_max(self):
        """
        Check that a file with an incomplete salt data is sensibly rejected
        (maximum corner case).
        """

        helpers.write_file(
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
        """
        Check that a file with an incomplete initialization vector is sensibly
        rejected (minimum corner case).
        """

        helpers.write_file(
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
        """
        Check that a file with an incomplete initialization vector is sensibly
        rejected (maximum corner case).
        """

        helpers.write_file(
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
        """
        Check that a file with a misaligned encrypted data is sensibly rejected.
        """

        helpers.write_file(
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
        """
        Check that a file with an invalid magic number in its header is sensibly
        rejected.
        """

        helpers.write_file(
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
        """
        Check that a file with an unsupported version number in its header is
        sensibly rejected.
        """

        helpers.write_file(
            self.dbname,
            b'rvl\x00\xff\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22\x23')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Unsupported data version, expected b'2' but found b'\\xff'")

    def test_read_header_padding(self):
        """
        Check that a file with wrong padding at bytes [5:6) in its header is
        sensibly rejected.
        """

        helpers.write_file(
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
        """
        Check that a file with wrong padding at bytes [9:12) in its header is
        sensibly rejected.
        """

        helpers.write_file(
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
        """
        Check that using a wrong password to read a database is sensibly
        reported.
        """

        helpers.write_password_db(self.dbname, 'a', 'RAW CONTENT')

        storage = storepass.storage.Storage(self.dbname, 'b')
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception), "Incorrect password")

    def test_read_no_compressed_data(self):
        """
        Check that a file with compressed data of zero size is sensibly
        rejected.
        """

        helpers.write_password_db(self.dbname,
                                  DEFAULT_PASSWORD,
                                  '',
                                  compress=False)

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_plain()
        self.assertEqual(str(cm.exception), "Compressed data have zero size")

    def test_read_wrong_padding_length(self):
        """
        Check that a file with a wrong padding of compressed data (incorrect
        length) is sensibly rejected.
        """

        helpers.write_password_db(
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
        """
        Check that a file with a wrong padding of compressed data (incorrect
        bytes) is sensibly rejected.
        """

        helpers.write_password_db(
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
        """
        Check that a file with wrongly compressed data is sensibly rejected.
        """

        helpers.write_password_db(
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
        """
        Check that a file with wrongly encoded data is sensibly rejected.
        """

        helpers.write_password_db(self.dbname, DEFAULT_PASSWORD, b'\xff')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageReadException) as cm:
            _ = storage.read_plain()
        self.assertEqual(
            str(cm.exception),
            "Error decoding payload: 'utf-8' codec can't decode byte 0xff in "
            "position 0: invalid start byte")

    def test_read_generic_entry(self):
        """Check parsing of a single generic entry."""

        helpers.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            helpers.dedent('''\
                <?xml version="1.0" encoding="utf-8"?>
                <revelationdata version="0.4.14" dataversion="1">
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

    def test_write_plain(self):
        """Check that the plain writer can save raw database content."""

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        storage.write_plain('RAW CONTENT')

        data = helpers.read_password_db(self.dbname, DEFAULT_PASSWORD, self)
        self.assertEqual(data, 'RAW CONTENT')

    def test_write_invalid_file(self):
        """Check that an unwritable file is sensibly rejected."""

        storage = storepass.storage.Storage(os.getcwd(), DEFAULT_PASSWORD)
        with self.assertRaises(storepass.exc.StorageWriteException) as cm:
            storage.write_plain('')
        self.assertRegex(str(cm.exception), r"\[Errno 21\] Is a directory:")

    def test_write_generic_entry(self):
        """Check output of a single generic entry."""

        generic = storepass.model.Generic("E1 name", "E1 description", \
            "1546300800", "E1 notes", "E1 hostname", "E1 username", \
            "E1 password")
        root = storepass.model.Root([generic])

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        storage.write_tree(root)

        data = helpers.read_password_db(self.dbname, DEFAULT_PASSWORD, self)
        self.assertEqual(
            data,
            helpers.dedent('''\
                <?xml version="1.0" encoding="utf-8"?>
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
