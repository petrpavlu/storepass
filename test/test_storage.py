# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

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

    def tearDown(self):
        shutil.rmtree(self.testdir)

    def test_plain_reader(self):
        """Check that the plain reader can output raw database content."""

        dbname = os.path.join(self.testdir, 'pass.db')
        support.write_password_db(dbname, DEFAULT_PASSWORD, '''\
RAW CONTENT''')
        storage = storepass.storage.PlainReader(dbname, DEFAULT_PASSWORD)
        self.assertEqual(storage.data, '''\
RAW CONTENT''')

    def test_generic_entry(self):
        dbname = os.path.join(self.testdir, 'pass.db')
        support.write_password_db(dbname, DEFAULT_PASSWORD, '''\
<?xml version="1.0" encoding="utf-8"?>
<revelationdata version="0.4.14" dataversion="1">
        <entry type="generic">
                <name>E1 name</name>
                <description>E1 description</description>
                <updated>1546300800</updated>
                <notes>E1 notes</notes>
                <field id="generic-hostname">E1 hostname</field>
                <field id="generic-username">E1 username</field>
                <field id="generic-password">E1 password</field>
        </entry>
</revelationdata>''')
        storage = storepass.storage.TreeReader(dbname, DEFAULT_PASSWORD)
        root = storage.get_root_node()
        self.assertEqual(root.type, root.TYPE_ROOT)
