# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""End-to-end command line tests."""

import contextlib
import io
import unittest.mock

import storepass.cli.__main__
from . import helpers

DEFAULT_PASSWORD = 'qwerty'


class CLIMock:
    """Class grouping mocked functions and variables."""
    def __init__(self, getpass, stdout, stderr):
        self.getpass = getpass
        self.stdout = stdout
        self.stderr = stderr


@contextlib.contextmanager
def cli_context(args):
    """Create a mocked CLI context."""

    with unittest.mock.patch('getpass.getpass') as getpass, \
         unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as out, \
         unittest.mock.patch('sys.stderr', new_callable=io.StringIO) as err, \
         unittest.mock.patch('sys.argv', args):
        yield CLIMock(getpass, out, err)


class TestCLI(helpers.StorePassTestCase):
    def _init_database(self, filename):
        """Create a new empty password database."""

        with cli_context(['storepass-cli', '-f', filename, 'init']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), '')
            self.assertEqual(cli_mock.stderr.getvalue(), '')

    def test_help(self):
        """Check the basic --help output."""

        with cli_context(['storepass-cli', '--help']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                helpers.dedent2('''\
                    |usage: storepass-cli [-h] [-f PASSDB] [-v]
                    |                     {init,list,show,add,edit,delete,dump} ...
                    |
                    |positional arguments:
                    |  {init,list,show,add,edit,delete,dump}
                    |
                    |optional arguments:
                    |  -h, --help            show this help message and exit
                    |  -f PASSDB, --file PASSDB
                    |                        password database file (the default is
                    |                        ~/.storepass.db)
                    |  -v, --verbose         increase verbosity level
                    '''))
            self.assertEqual(cli_mock.stderr.getvalue(), '')

    def test_error(self):
        """
        Check that a simple error about a missing database file is sensibly
        reported.
        """

        with cli_context(['storepass-cli', '-f', 'missing.db', 'list']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), '')
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                helpers.dedent('''\
                    storepass-cli: error: failed to load password database \'missing.db\': [Errno 2] No such file or directory: \'missing.db\'
                    '''))

    def test_init(self):
        """
        Check that the init subcommand can be used to create a new empty
        password database.
        """

        # Create a new empty password database.
        with cli_context(['storepass-cli', '-f', self.dbname, 'init']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), '')
            self.assertEqual(cli_mock.stderr.getvalue(), '')

        # Read the database back and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname, 'dump']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                helpers.dedent('''\
                    <?xml version="1.0" encoding="utf-8"?>
                    <revelationdata dataversion="1" />
                    '''))
            self.assertEqual(cli_mock.stderr.getvalue(), '')

        # Check that no entries get listed.
        with cli_context(['storepass-cli', '-f', self.dbname, 'list']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), '')
            self.assertEqual(cli_mock.stderr.getvalue(), '')

    def test_init_overwrite(self):
        """
        Check that the init subcommand does not overwrite an already existing
        file.
        """

        # Write an empty password database.
        helpers.write_file(self.dbname, b'')

        # Check that trying to create a password database with the same name is
        # sensibly rejected.
        with cli_context(['storepass-cli', '-f', self.dbname, 'init']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), '')
            self.assertRegex(
                cli_mock.stderr.getvalue(),
                helpers.dedent('''\
                    storepass-cli: error: failed to write password database '.*': \\[Errno 17\\] File exists: '.*'
                    '''))

    def test_add(self):
        """
        Check that a single entry can be added to a password database.
        """

        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new entry.
        with cli_context(
                 ['storepass-cli', '-f', self.dbname, 'add', 'E1 name']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), '')
            self.assertEqual(cli_mock.stderr.getvalue(), '')

        # Read the database back and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname, 'dump']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                helpers.dedent('''\
                    <?xml version="1.0" encoding="utf-8"?>
                    <revelationdata dataversion="1">
                    \t<entry type="generic">
                    \t\t<name>E1 name</name>
                    \t</entry>
                    </revelationdata>
                    '''))
            self.assertEqual(cli_mock.stderr.getvalue(), '')

        # Check that the entry is listed as expected.
        with cli_context(['storepass-cli', '-f', self.dbname, 'list']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                helpers.dedent('''\
                    - E1 name
                    '''))
            self.assertEqual(cli_mock.stderr.getvalue(), '')

    def test_add_generic(self):
        """
        Check that a complete generic entry can be added to a password database.
        """

        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new generic entry.
        with cli_context(
                 ['storepass-cli', '-f', self.dbname, 'add',
                  '--description', 'E1 description', '--notes', 'E1 notes',
                  '--hostname', 'E1 hostname', '--username', 'E1 username',
                  '--password', 'E1 name']) \
             as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, "E1 password"]
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            self.assertEqual(cli_mock.getpass.call_count, 2)
            self.assertEqual(cli_mock.stdout.getvalue(), '')
            self.assertEqual(cli_mock.stderr.getvalue(), '')

        # Read the database back and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname, 'dump']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                helpers.dedent('''\
                    <?xml version="1.0" encoding="utf-8"?>
                    <revelationdata dataversion="1">
                    \t<entry type="generic">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="generic-hostname">E1 hostname</field>
                    \t\t<field id="generic-username">E1 username</field>
                    \t\t<field id="generic-password">E1 password</field>
                    \t</entry>
                    </revelationdata>
                    '''))
            self.assertEqual(cli_mock.stderr.getvalue(), '')

        # Check that the entry is listed as expected.
        with cli_context(['storepass-cli', '-f', self.dbname, 'list']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                helpers.dedent('''\
                    - E1 name [E1 hostname]: E1 description
                    '''))
            self.assertEqual(cli_mock.stderr.getvalue(), '')

    def test_add_folder(self):
        """
        Check that a complete folder entry can be added to a password database.
        """

        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new folder entry.
        with cli_context(
                 ['storepass-cli', '-f', self.dbname, 'add',
                  '--type', 'folder', '--description', 'E1 description',
                  '--notes', 'E1 notes', 'E1 name']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), '')
            self.assertEqual(cli_mock.stderr.getvalue(), '')

        # Read the database back and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname, 'dump']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                helpers.dedent('''\
                    <?xml version="1.0" encoding="utf-8"?>
                    <revelationdata dataversion="1">
                    \t<entry type="folder">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<notes>E1 notes</notes>
                    \t</entry>
                    </revelationdata>
                    '''))
            self.assertEqual(cli_mock.stderr.getvalue(), '')

        # Check that the entry is listed as expected.
        with cli_context(['storepass-cli', '-f', self.dbname, 'list']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                helpers.dedent('''\
                    + E1 name: E1 description
                    '''))
            self.assertEqual(cli_mock.stderr.getvalue(), '')

    def test_add_nested(self):
        """
        Check that nested entries can be added to a password database.
        """

        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new folder entry.
        with cli_context(
                 ['storepass-cli', '-f', self.dbname, 'add',
                  '--type', 'folder', 'E1 name']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), '')
            self.assertEqual(cli_mock.stderr.getvalue(), '')

        # Add a nested folder entry.
        with cli_context(
                 ['storepass-cli', '-f', self.dbname, 'add',
                  '--type', 'folder', 'E1 name/E2 name']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), '')
            self.assertEqual(cli_mock.stderr.getvalue(), '')

        # Add a nested generic entry.
        with cli_context(
                 ['storepass-cli', '-f', self.dbname, 'add',
                  'E1 name/E2 name/E3 name']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            #self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), '')
            self.assertEqual(cli_mock.stderr.getvalue(), '')

        # Read the database back and dump its XML content.
        with cli_context(['storepass-cli', '-f', self.dbname, 'dump']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                helpers.dedent('''\
                    <?xml version="1.0" encoding="utf-8"?>
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
            self.assertEqual(cli_mock.stderr.getvalue(), '')

        # Check that the entries are listed as expected.
        with cli_context(['storepass-cli', '-f', self.dbname, 'list']) \
             as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                helpers.dedent2('''\
                    |+ E1 name
                    |  + E2 name
                    |    - E3 name
                    '''))
            self.assertEqual(cli_mock.stderr.getvalue(), '')
