# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""End-to-end command line tests."""

import contextlib
import io
import os
import time
import unittest.mock

import storepass.cli.__main__
from . import util

DEFAULT_PASSWORD = 'qwerty'


class CLIMock:
    """Class grouping mocked functions and variables."""
    def __init__(self, getpass, stdout, stderr):
        self.getpass = getpass
        self.stdout = stdout
        self.stderr = stderr


@contextlib.contextmanager
def cli_context(args, timezone=None):
    """Create a mocked CLI context."""

    with unittest.mock.patch('getpass.getpass') as getpass, \
         unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as out, \
         unittest.mock.patch('sys.stderr', new_callable=io.StringIO) as err, \
         unittest.mock.patch('sys.argv', args):
        if timezone is not None:
            # Save the current timezone and set the desired one.
            try:
                prev_tz = os.environ['TZ']
            except KeyError:
                prev_tz = None
            os.environ['TZ'] = timezone
            time.tzset()

        yield CLIMock(getpass, out, err)

        if timezone is not None:
            # Restore the original timezone settings.
            if prev_tz is None:
                del os.environ['TZ']
            else:
                os.environ['TZ'] = prev_tz
            time.tzset()


class TestCLI(util.StorePassTestCase):
    def _init_database(self, filename):
        """Create a new empty password database."""

        with cli_context(['storepass-cli', '-f', filename,
                          'init']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_help(self):
        """Check the basic --help output."""

        with cli_context(['storepass-cli', '--help']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent2("""\
                    |usage: storepass-cli [-h] [-f PASSDB] [-v] {init,list,show,add,edit,delete,dump} ...
                    |
                    |positional arguments:
                    |  {init,list,show,add,edit,delete,dump}
                    |
                    |optional arguments:
                    |  -h, --help            show this help message and exit
                    |  -f PASSDB, --file PASSDB
                    |                        password database file (the default is ~/.storepass.db)
                    |  -v, --verbose         increase verbosity level
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_error(self):
        """
        Check that a simple error about a missing database file is sensibly
        reported.
        """

        with cli_context(['storepass-cli', '-f', 'missing.db',
                          'list']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                util.dedent("""\
                    storepass-cli: error: failed to load password database \'missing.db\': [Errno 2] No such file or directory: \'missing.db\'
                    """))

    def test_init(self):
        """
        Check that the init subcommand can be used to create a new empty
        password database.
        """

        # Create a new empty password database.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'init']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Read the database and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'dump']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    <?xml version='1.0' encoding='UTF-8'?>
                    <revelationdata dataversion="1" />
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Check that no entries get listed.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'list']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_init_overwrite(self):
        """
        Check that the init subcommand does not overwrite an already existing
        file.
        """

        # Write an empty password database.
        util.write_file(self.dbname, b'')

        # Check that trying to create a password database with the same name is
        # sensibly rejected.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'init']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertRegex(
                cli_mock.stderr.getvalue(),
                util.dedent("""\
                    storepass-cli: error: failed to save password database '.*': \\[Errno 17\\] File exists: '.*'
                    """))

    def test_add(self):
        """Check that a single entry can be added to a password database."""

        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new entry.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'add',
             'E1 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Read the database and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'dump']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertRegex(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="generic">
                    \t\t<name>E1 name</name>
                    \t\t<updated>[0-9]+</updated>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_generic(self):
        """
        Check that a complete generic entry can be added to a password
        database.
        """

        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new generic entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--description',
                'E1 description', '--notes', 'E1 notes', '--hostname',
                'E1 hostname', '--username', 'E1 username', '--password',
                'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, "E1 password"]
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            self.assertEqual(cli_mock.getpass.call_count, 2)
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Read the database and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'dump']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertRegex(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="generic">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="generic-hostname">E1 hostname</field>
                    \t\t<field id="generic-username">E1 username</field>
                    \t\t<field id="generic-password">E1 password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_folder(self):
        """
        Check that a complete folder entry can be added to a password database.
        """

        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new folder entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'folder',
                '--description', 'E1 description', '--notes', 'E1 notes',
                'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Read the database and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'dump']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertRegex(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="folder">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_folder_options(self):
        """
        Check that options that are invalid for the folder entry type are
        sensibly rejected.
        """

        # Try to add a new folder entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'folder',
                '--hostname', 'E1 hostname', '--username', 'E1 username',
                '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                util.dedent("""\
                    storepass-cli: error: option --hostname is not valid for entry type 'folder'
                    storepass-cli: error: option --username is not valid for entry type 'folder'
                    storepass-cli: error: option --password is not valid for entry type 'folder'
                    """))

    def test_add_nested(self):
        """Check that nested entries can be added to a password database."""

        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new folder entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'folder',
                'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Add a nested folder entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'folder',
                'E1 name/E2 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Add a nested generic entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add',
                'E1 name/E2 name/E3 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Read the database and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'dump']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertRegex(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="folder">
                    \t\t<name>E1 name</name>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<entry type="folder">
                    \t\t\t<name>E2 name</name>
                    \t\t\t<updated>[0-9]+</updated>
                    \t\t\t<entry type="generic">
                    \t\t\t\t<name>E3 name</name>
                    \t\t\t\t<updated>[0-9]+</updated>
                    \t\t\t</entry>
                    \t\t</entry>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_invalid_path(self):
        """
        Check that adding a new entry under a non-existent path is sensibly
        rejected.
        """

        # Create a new empty password database.
        self._init_database(self.dbname)

        # Try to add a nested generic entry with an invalid path.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'add',
             'E1 name/E2 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                util.dedent("""\
                    storepass-cli: error: Entry 'E1 name' (element #1 in 'E1 name') does not exist
                    """))

    def test_add_present(self):
        """
        Check that adding a new entry with the same name as an existing entry
        is sensibly rejected.
        """

        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new entry.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'add',
             'E1 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Try to add a new entry with the same name.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'add',
             'E1 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                util.dedent("""\
                    storepass-cli: error: Entry 'E1 name' already exists
                    """))

    def test_delete(self):
        """
        Check that a single entry can be deleted from a password database.
        """

        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <?xml version='1.0' encoding='UTF-8'?>
                <revelationdata dataversion="1">
                \t<entry type="generic">
                \t\t<name>E1 name</name>
                \t</entry>
                </revelationdata>
                '''))

        # Delete the entry.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'delete',
             'E1 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Read the database and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'dump']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    <?xml version='1.0' encoding='UTF-8'?>
                    <revelationdata dataversion="1" />
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_delete_nested(self):
        """
        Check that nested entries can be deleted from a password database.
        """

        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<name>E1 name</name>
                \t\t<entry type="folder">
                \t\t\t<name>E2 name</name>
                \t\t\t<entry type="generic">
                \t\t\t\t<name>E3 name</name>
                \t\t\t</entry>
                \t\t</entry>
                \t</entry>
                </revelationdata>
                '''))

        # Delete the nested generic entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'delete',
                'E1 name/E2 name/E3 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Delete the nested folder entry.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'delete',
             'E1 name/E2 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Read the database and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'dump']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    <?xml version='1.0' encoding='UTF-8'?>
                    <revelationdata dataversion="1">
                    \t<entry type="folder">
                    \t\t<name>E1 name</name>
                    \t</entry>
                    </revelationdata>
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_delete_invalid_path(self):
        """Check that deleting a non-existent entry is sensibly rejected."""

        # Create a new empty password database.
        self._init_database(self.dbname)

        # Try to delete a nested generic entry with an invalid path.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'delete',
             'E1 name/E2 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                util.dedent("""\
                    storepass-cli: error: Entry 'E1 name' (element #1 in 'E1 name/E2 name') does not exist
                    """))

    def test_delete_non_empty(self):
        """Check that deleting a non-empty folder is sensibly rejected."""

        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<name>E1 name</name>
                \t\t<entry type="generic">
                \t\t\t<name>E2 name</name>
                \t\t</entry>
                \t</entry>
                </revelationdata>
                '''))

        # Try to delete the top folder.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'delete',
             'E1 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                util.dedent("""\
                    storepass-cli: error: Entry 'E1 name' is not empty
                    """))

        # Read the database and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'dump']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    <revelationdata dataversion="1">
                    \t<entry type="folder">
                    \t\t<name>E1 name</name>
                    \t\t<entry type="generic">
                    \t\t\t<name>E2 name</name>
                    \t\t</entry>
                    \t</entry>
                    </revelationdata>
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list(self):
        """Check that a single entry can be listed."""

        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="generic">
                \t\t<name>E1 name</name>
                \t</entry>
                </revelationdata>
                '''))

        # Check that the entry is listed as expected.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'list']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    - E1 name
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_generic(self):
        """Check that a complete generic entry can be listed."""

        # Create a test database.
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

        # Check that the entry is listed as expected.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'list']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_folder(self):
        """Check that a complete folder entry can be listed."""

        # Create a test database.
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

        # Check that the entry is listed as expected.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'list']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    + E1 name: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_nested(self):
        """Check that nested entries can be listed."""

        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<name>E1 name</name>
                \t\t<entry type="folder">
                \t\t\t<name>E2 name</name>
                \t\t\t<entry type="generic">
                \t\t\t\t<name>E3 name</name>
                \t\t\t</entry>
                \t\t</entry>
                \t</entry>
                \t<entry type="folder">
                \t\t<name>E4 name</name>
                \t</entry>
                </revelationdata>
                '''))

        # Check that the entries are listed as expected.
        with cli_context(['storepass-cli', '-f', self.dbname,
                          'list']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent2("""\
                    |+ E1 name
                    |  + E2 name
                    |    - E3 name
                    |+ E4 name
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show(self):
        """Check that details of a single entry can be displayed."""

        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="generic">
                \t\t<name>E1 name</name>
                \t</entry>
                </revelationdata>
                '''))

        # Check that the entry is displayed as expected.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'show',
             'E1 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    + E1 name (password entry)
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_timezone(self):
        """
        Check that timezone settings are correctly taken into effect when
        displaying details of a single entry.
        """

        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="generic">
                \t\t<name>E1 name</name>
                \t\t<updated>1546300800</updated>
                \t</entry>
                </revelationdata>
                '''))

        # Check the display with the GMT timezone.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'show', 'E1 name'],
                timezone='GMT') as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent2("""\
                    |+ E1 name (password entry)
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Check the display with the GMT+1 timezone.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'show', 'E1 name'],
                timezone='GMT-1') as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent2("""\
                    |+ E1 name (password entry)
                    |  - Last modified: Tue Jan  1 01:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_generic(self):
        """Check that details of a complete generic entry can be displayed."""

        # Create a test database.
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

        # Check that the entry is displayed as expected.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'show', 'E1 name'],
                timezone='GMT') as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent2("""\
                    |+ E1 name (password entry)
                    |  - Hostname: E1 hostname
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_folder(self):
        """Check that details of a complete folder entry can be displayed."""

        # Create a test database.
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

        # Check that the entry is displayed as expected.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'show', 'E1 name'],
                timezone='GMT') as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent2("""\
                    |+ E1 name (folder)
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_nested(self):
        """Check that nested entries can be displayed."""

        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<name>E1 name</name>
                \t\t<entry type="folder">
                \t\t\t<name>E2 name</name>
                \t\t\t<entry type="generic">
                \t\t\t\t<name>E3 name</name>
                \t\t\t</entry>
                \t\t</entry>
                \t</entry>
                \t<entry type="folder">
                \t\t<name>E4 name</name>
                \t</entry>
                </revelationdata>
                '''))

        # Check that the entries are displayed as expected.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'show',
             'E1 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    + E1 name (folder)
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'show',
             'E1 name/E2 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    + E2 name (folder)
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        with cli_context([
                'storepass-cli', '-f', self.dbname, 'show',
                'E1 name/E2 name/E3 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    + E3 name (password entry)
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'show',
             'E4 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                util.dedent("""\
                    + E4 name (folder)
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")
