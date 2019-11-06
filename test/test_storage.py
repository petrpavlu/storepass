# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import storepass.model
import storepass.storage
from . import support

import os.path
import shutil
import tempfile
import unittest

DEFAULT_PASSWORD = 'qwerty'

class TestStorage(unittest.TestCase):
    def setUp(self):
        self.testdir = tempfile.mkdtemp()

        # Set default database name.
        self.dbname = os.path.join(self.testdir, 'pass.db')

    def tearDown(self):
        shutil.rmtree(self.testdir)

    def test_plain_reader(self):
        """Check that the plain reader can output raw database content."""

        support.write_password_db(self.dbname, DEFAULT_PASSWORD, 'RAW CONTENT')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        data = storage.read_plain()
        self.assertEqual(data, 'RAW CONTENT')

    def test_header_size_min(self):
        """
        Check that a file with an incomplete header is sensibly rejected
        (minimum corner case).
        """

        support.write_file(self.dbname, b'')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception),
            "File header is incomplete, expected '12' bytes but found '0'")

    def test_header_size_max(self):
        """
        Check that a file with an incomplete header is sensibly rejected
        (maximum corner case).
        """

        support.write_file(self.dbname,
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception),
            "File header is incomplete, expected '12' bytes but found '11'")

    def test_salt_size_min(self):
        """
        Check that a file with an incomplete salt data is sensibly rejected
        (minimum corner case).
        """

        support.write_file(self.dbname,
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Salt record is incomplete, expected '8' bytes but found '0'")

    def test_salt_size_max(self):
        """
        Check that a file with an incomplete salt data is sensibly rejected
        (maximum corner case).
        """

        support.write_file(self.dbname,
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Salt record is incomplete, expected '8' bytes but found '7'")

    def test_init_size_min(self):
        """
        Check that a file with an incomplete initialization vector is sensibly
        rejected (minimum corner case).
        """

        support.write_file(self.dbname,
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Initialization vector is incomplete, expected '16' bytes but "
            "found '0'")

    def test_init_size_max(self):
        """
        Check that a file with an incomplete initialization vector is sensibly
        rejected (maximum corner case).
        """

        support.write_file(self.dbname,
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Initialization vector is incomplete, expected '16' bytes but "
            "found '15'")

    def test_encrypted_alignment(self):
        """
        Check that a file with a misaligned encrypted data is sensibly rejected.
        """

        support.write_file(self.dbname,
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22\x23\x24')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Data record with size of '1' bytes is not 16-byte aligned")

    def test_header_magic(self):
        """
        Check that a file with an invalid magic number in its header is sensibly
        rejected.
        """

        support.write_file(self.dbname,
            b'\xff\xff\xff\xff\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22\x23')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Invalid magic number, expected b'rvl\\x00' but found "
            "b'\\xff\\xff\\xff\\xff'")

    def test_header_version(self):
        """
        Check that a file with an unsupported version number in its header is
        sensibly rejected.
        """

        support.write_file(self.dbname,
            b'rvl\x00\xff\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22\x23')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Unsupported data version, expected b'2' but found b'\\xff'")

    def test_header_padding(self):
        """
        Check that a file with wrong padding at bytes [5:6) in its header is
        sensibly rejected.
        """

        support.write_file(self.dbname,
            b'rvl\x00\x02\xff\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22\x23')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Non-zero header padding at bytes [5:6), found b'\\xff'")

    def test_header_padding2(self):
        """
        Check that a file with wrong padding at bytes [9:12) in its header is
        sensibly rejected.
        """

        support.write_file(self.dbname,
            b'rvl\x00\x02\x00\x06\x07\x08\xff\xff\xff\x0c\x0d\x0e\x0f'
            b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
            b'\x20\x21\x22\x23')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Non-zero header padding at bytes [9:12), found b'\\xff\\xff\\xff'")

    def test_password(self):
        """
        Check that using a wrong password to read a database is sensibly
        reported.
        """

        support.write_password_db(self.dbname, 'a', 'RAW CONTENT')

        storage = storepass.storage.Storage(self.dbname, 'b')
        with self.assertRaises(storepass.storage.ReadException) as cm:
            storage.read_plain()
        self.assertEqual(str(cm.exception), "Incorrect password")

    def test_no_compressed_data(self):
        """
        Check that a file with compressed data of zero size is sensibly
        rejected.
        """

        support.write_password_db(self.dbname, DEFAULT_PASSWORD, '',
            compress=False)

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            data = storage.read_plain()
        self.assertEqual(str(cm.exception), "Compressed data have zero size")

    def test_wrong_padding_length(self):
        """
        Check that a file with a wrong padding of compressed data (incorrect
        length) is sensibly rejected.
        """

        support.write_password_db(self.dbname, DEFAULT_PASSWORD,
            '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x10',
            compress=False)

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            data = storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Compressed data have incorrect padding, length '16' is bigger "
            "than '15' bytes")

    def test_wrong_padding_bytes(self):
        """
        Check that a file with a wrong padding of compressed data (incorrect
        bytes) is sensibly rejected.
        """

        support.write_password_db(self.dbname, DEFAULT_PASSWORD,
            '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x02',
            compress=False)

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            data = storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Compressed data have incorrect padding, expected b'\\x02\\x02' "
            "but found b'\\x0e\\x02'")

    def test_wrong_compression(self):
        """
        Check that a file with wrongly compressed data is sensibly rejected.
        """

        support.write_password_db(self.dbname, DEFAULT_PASSWORD,
            '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x01',
            compress=False)

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            data = storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Error -3 while decompressing data: incorrect header check")

    def test_wrong_utf8(self):
        """
        Check that a file with wrongly encoded data is sensibly rejected.
        """

        support.write_password_db(self.dbname, DEFAULT_PASSWORD, b'\xff')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        with self.assertRaises(storepass.storage.ReadException) as cm:
            data = storage.read_plain()
        self.assertEqual(str(cm.exception),
            "Error decoding payload: 'utf-8' codec can't decode byte 0xff in "
            "position 0: invalid start byte")

    def test_generic_entry(self):
        """Check parsing of a single generic entry."""

        support.write_password_db(self.dbname, DEFAULT_PASSWORD, '''\
<?xml version="1.0" encoding="utf-8"?>
<revelationdata version="0.4.14" dataversion="1">
        <entry type="generic">
                <name>E1 name</name>
                <description>E1 description</description>
                <updated>1546300800</updated>
                <notes>E1 notes</notes>
                <field id="generic-username">E1 username</field>
                <field id="generic-password">E1 password</field>
                <field id="generic-hostname">E1 hostname</field>
        </entry>
</revelationdata>''')

        storage = storepass.storage.Storage(self.dbname, DEFAULT_PASSWORD)
        root = storage.read_tree()

        self.assertTrue(isinstance(root, storepass.model.Root))
        self.assertEqual(len(root.children), 1)

        c0 = root.children[0]
        self.assertIs(type(c0), storepass.model.Generic)
        self.assertEqual(c0.name, "E1 name")
        self.assertEqual(c0.description, "E1 description")
        self.assertEqual(c0.updated, "1546300800")
        self.assertEqual(c0.notes, "E1 notes")
        self.assertEqual(c0.username, "E1 username")
        self.assertEqual(c0.password, "E1 password")
        self.assertEqual(c0.hostname, "E1 hostname")
