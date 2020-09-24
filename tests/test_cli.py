# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""End-to-end command-line tests."""

import contextlib
import io
import os
import time
import unittest.mock

import storepass.cli.__main__
from . import utils

DEFAULT_PASSWORD = 'qwerty'


class CLIMock:
    """Class grouping mocked functions and variables."""
    def __init__(self, getpass, stdout, stderr):
        """Initialize a CLI mock object."""
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


class TestCLI(utils.StorePassTestCase):
    """End-to-end command-line tests."""
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
                utils.dedent2("""\
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
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_help(self):
        """Check the --help output for the add command."""
        with cli_context(['storepass-cli', 'add', '--help']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                utils.dedent2("""\
                    |usage: storepass-cli add [-h]
                    |                         [--type {folder,credit-card,crypto-key,database,door,email,ftp,generic,phone,remote-desktop,shell,vnc,website}]
                    |                         [--description DESC] [--notes NOTES]
                    |                         [--card-number VALUE] [--card-type VALUE]
                    |                         [--ccv VALUE] [--certificate VALUE] [--code VALUE]
                    |                         [--database VALUE] [--domain VALUE] [--email VALUE]
                    |                         [--expiry-date VALUE] [--hostname VALUE]
                    |                         [--keyfile VALUE] [--location VALUE] [--password]
                    |                         [--phone-number VALUE] [--pin VALUE] [--port VALUE]
                    |                         [--url VALUE] [--username VALUE]
                    |                         ENTRY
                    |
                    |add a new password entry
                    |
                    |positional arguments:
                    |  ENTRY                 password entry
                    |
                    |optional arguments:
                    |  -h, --help            show this help message and exit
                    |  --type {folder,credit-card,crypto-key,database,door,email,ftp,generic,phone,remote-desktop,shell,vnc,website}
                    |                        entry type (the default is generic)
                    |
                    |optional arguments valid for all entry types:
                    |  --description DESC    set the entry description to the specified value
                    |  --notes NOTES         set the entry notes to the specified value
                    |
                    |optional arguments valid for specific entry types:
                    |  --card-number VALUE   set the card-number property to the specified value
                    |  --card-type VALUE     set the card-type property to the specified value
                    |  --ccv VALUE           set the ccv property to the specified value
                    |  --certificate VALUE   set the certificate property to the specified value
                    |  --code VALUE          set the code property to the specified value
                    |  --database VALUE      set the database property to the specified value
                    |  --domain VALUE        set the domain property to the specified value
                    |  --email VALUE         set the email property to the specified value
                    |  --expiry-date VALUE   set the expiry-date property to the specified value
                    |  --hostname VALUE      set the hostname property to the specified value
                    |  --keyfile VALUE       set the keyfile property to the specified value
                    |  --location VALUE      set the location property to the specified value
                    |  --password            prompt for a value of the password property
                    |  --phone-number VALUE  set the phone-number property to the specified value
                    |  --pin VALUE           set the pin property to the specified value
                    |  --port VALUE          set the port property to the specified value
                    |  --url VALUE           set the url property to the specified value
                    |  --username VALUE      set the username property to the specified value
                    |
                    |property validity for entry types:
                    |  folder:               --
                    |  credit-card:          card-type, card-number, expiry-date, ccv, pin
                    |  crypto-key:           hostname, certificate, keyfile, password
                    |  database:             hostname, username, password, database
                    |  door:                 location, code
                    |  email:                email, hostname, username, password
                    |  ftp:                  hostname, port, username, password
                    |  generic:              hostname, username, password
                    |  phone:                phone-number, pin
                    |  remote-desktop:       hostname, port, username, password
                    |  shell:                hostname, domain, username, password
                    |  vnc:                  hostname, port, username, password
                    |  website:              url, username, email, password
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_error(self):
        """Check reporting of a simple error about a missing database."""
        with cli_context(['storepass-cli', '-f', 'missing.db',
                          'list']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Failed to load password database \'missing.db\': [Errno 2] No such file or directory: \'missing.db\'
                    """))

    def test_init(self):
        """Check that the init command creates a new empty database."""
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
                utils.dedent("""\
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
        """Check that the init command does not overwrite an existing file."""
        # Write an empty password database.
        utils.write_file(self.dbname, b'')

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
                utils.dedent("""\
                    Failed to save password database '.*': \\[Errno 17\\] File exists: '.*'
                    """))

    def test_add(self):
        """Check that a single entry can be added to a database."""
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="generic">
                    \t\t<name>E1 name</name>
                    \t\t<updated>[0-9]+</updated>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_nested(self):
        """Check that nested entries can be added to a database."""
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
                utils.dedent("""\
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
        """Check rejection to add a new entry under a non-existent path."""
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
                utils.dedent("""\
                    Entry 'E1 name' (element #1 in 'E1 name') does not exist
                    """))

    def test_add_duplicated(self):
        """Check rejection to add a new entry with a duplicate name."""
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
                utils.dedent("""\
                    Entry 'E1 name' already exists
                    """))

    def test_add_empty(self):
        """Check rejection to add a new entry with an empty name."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Try to add a new entry with an empty name.
        with cli_context(['storepass-cli', '-f', self.dbname, 'add',
                          '']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Specified entry name is empty
                    """))

    def test_add_folder(self):
        """Check that a folder entry can be added to a database."""
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
                utils.dedent("""\
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
        """Check rejection of invalid options for the folder type."""
        # Try to add a new folder entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'folder',
                '--card-number', 'E1 card number', '--card-type',
                'E1 card type', '--ccv', 'E1 CCV', '--certificate',
                'E1 certificate', '--code', 'E1 code', '--database',
                'E1 database', '--domain', 'E1 domain', '--email', 'E1 email',
                '--expiry-date', 'E1 expiry date', '--hostname', 'E1 hostname',
                '--keyfile', 'E1 keyfile', '--location', 'E1 location',
                '--password', '--phone-number', 'E1 phone number', '--pin',
                'E1 PIN', '--port', 'E1 port', '--url', 'E1 URL', '--username',
                'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'card-number' is not valid for entry type 'folder'
                    Property 'card-type' is not valid for entry type 'folder'
                    Property 'ccv' is not valid for entry type 'folder'
                    Property 'certificate' is not valid for entry type 'folder'
                    Property 'code' is not valid for entry type 'folder'
                    Property 'database' is not valid for entry type 'folder'
                    Property 'domain' is not valid for entry type 'folder'
                    Property 'email' is not valid for entry type 'folder'
                    Property 'expiry-date' is not valid for entry type 'folder'
                    Property 'hostname' is not valid for entry type 'folder'
                    Property 'keyfile' is not valid for entry type 'folder'
                    Property 'location' is not valid for entry type 'folder'
                    Property 'password' is not valid for entry type 'folder'
                    Property 'phone-number' is not valid for entry type 'folder'
                    Property 'pin' is not valid for entry type 'folder'
                    Property 'port' is not valid for entry type 'folder'
                    Property 'url' is not valid for entry type 'folder'
                    Property 'username' is not valid for entry type 'folder'
                    """))

    def test_add_credit_card(self):
        """Check that a credit-card entry can be added to a database."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new credit-card entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type',
                'credit-card', '--description', 'E1 description', '--notes',
                'E1 notes', '--card-type', 'E1 card type', '--card-number',
                'E1 card number', '--expiry-date', 'E1 expiry date', '--ccv',
                'E1 CCV', '--pin', 'E1 PIN', 'E1 name'
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="creditcard">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="creditcard-cardtype">E1 card type</field>
                    \t\t<field id="creditcard-cardnumber">E1 card number</field>
                    \t\t<field id="creditcard-expirydate">E1 expiry date</field>
                    \t\t<field id="creditcard-ccv">E1 CCV</field>
                    \t\t<field id="generic-pin">E1 PIN</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_credit_card_options(self):
        """Check rejection of invalid options for the credit-card type."""
        # Try to add a new credit-card entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type',
                'credit-card', '--card-number', 'E1 card number',
                '--card-type', 'E1 card type', '--ccv', 'E1 CCV',
                '--certificate', 'E1 certificate', '--code', 'E1 code',
                '--database', 'E1 database', '--domain', 'E1 domain',
                '--email', 'E1 email', '--expiry-date', 'E1 expiry date',
                '--hostname', 'E1 hostname', '--keyfile', 'E1 keyfile',
                '--location', 'E1 location', '--password', '--phone-number',
                'E1 phone number', '--pin', 'E1 PIN', '--port', 'E1 port',
                '--url', 'E1 URL', '--username', 'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'certificate' is not valid for entry type 'credit-card'
                    Property 'code' is not valid for entry type 'credit-card'
                    Property 'database' is not valid for entry type 'credit-card'
                    Property 'domain' is not valid for entry type 'credit-card'
                    Property 'email' is not valid for entry type 'credit-card'
                    Property 'hostname' is not valid for entry type 'credit-card'
                    Property 'keyfile' is not valid for entry type 'credit-card'
                    Property 'location' is not valid for entry type 'credit-card'
                    Property 'password' is not valid for entry type 'credit-card'
                    Property 'phone-number' is not valid for entry type 'credit-card'
                    Property 'port' is not valid for entry type 'credit-card'
                    Property 'url' is not valid for entry type 'credit-card'
                    Property 'username' is not valid for entry type 'credit-card'
                    """))

    def test_add_crypto_key(self):
        """Check that a crypto-key entry can be added to a database."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new crypto-key entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type',
                'crypto-key', '--description', 'E1 description', '--notes',
                'E1 notes', '--hostname', 'E1 hostname', '--certificate',
                'E1 certificate', '--keyfile', 'E1 keyfile', '--password',
                'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1 password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="cryptokey">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="generic-hostname">E1 hostname</field>
                    \t\t<field id="generic-certificate">E1 certificate</field>
                    \t\t<field id="generic-keyfile">E1 keyfile</field>
                    \t\t<field id="generic-password">E1 password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_crypto_key_options(self):
        """Check rejection of invalid options for the crypto-key type."""
        # Try to add a new crypto-key entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type',
                'crypto-key', '--card-number', 'E1 card number', '--card-type',
                'E1 card type', '--ccv', 'E1 CCV', '--certificate',
                'E1 certificate', '--code', 'E1 code', '--database',
                'E1 database', '--domain', 'E1 domain', '--email', 'E1 email',
                '--expiry-date', 'E1 expiry date', '--hostname', 'E1 hostname',
                '--keyfile', 'E1 keyfile', '--location', 'E1 location',
                '--password', '--phone-number', 'E1 phone number', '--pin',
                'E1 PIN', '--port', 'E1 port', '--url', 'E1 URL', '--username',
                'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'card-number' is not valid for entry type 'crypto-key'
                    Property 'card-type' is not valid for entry type 'crypto-key'
                    Property 'ccv' is not valid for entry type 'crypto-key'
                    Property 'code' is not valid for entry type 'crypto-key'
                    Property 'database' is not valid for entry type 'crypto-key'
                    Property 'domain' is not valid for entry type 'crypto-key'
                    Property 'email' is not valid for entry type 'crypto-key'
                    Property 'expiry-date' is not valid for entry type 'crypto-key'
                    Property 'location' is not valid for entry type 'crypto-key'
                    Property 'phone-number' is not valid for entry type 'crypto-key'
                    Property 'pin' is not valid for entry type 'crypto-key'
                    Property 'port' is not valid for entry type 'crypto-key'
                    Property 'url' is not valid for entry type 'crypto-key'
                    Property 'username' is not valid for entry type 'crypto-key'
                    """))

    def test_add_database(self):
        """Check that a database entry can be added to a database."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new database entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type',
                'database', '--description', 'E1 description', '--notes',
                'E1 notes', '--hostname', 'E1 hostname', '--username',
                'E1 username', '--password', '--database', 'E1 database',
                'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1 password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="database">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="generic-hostname">E1 hostname</field>
                    \t\t<field id="generic-username">E1 username</field>
                    \t\t<field id="generic-password">E1 password</field>
                    \t\t<field id="generic-database">E1 database</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_database_options(self):
        """Check rejection of invalid options for the database type."""
        # Try to add a new database entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type',
                'database', '--card-number', 'E1 card number', '--card-type',
                'E1 card type', '--ccv', 'E1 CCV', '--certificate',
                'E1 certificate', '--code', 'E1 code', '--database',
                'E1 database', '--domain', 'E1 domain', '--email', 'E1 email',
                '--expiry-date', 'E1 expiry date', '--hostname', 'E1 hostname',
                '--keyfile', 'E1 keyfile', '--location', 'E1 location',
                '--password', '--phone-number', 'E1 phone number', '--pin',
                'E1 PIN', '--port', 'E1 port', '--url', 'E1 URL', '--username',
                'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'card-number' is not valid for entry type 'database'
                    Property 'card-type' is not valid for entry type 'database'
                    Property 'ccv' is not valid for entry type 'database'
                    Property 'certificate' is not valid for entry type 'database'
                    Property 'code' is not valid for entry type 'database'
                    Property 'domain' is not valid for entry type 'database'
                    Property 'email' is not valid for entry type 'database'
                    Property 'expiry-date' is not valid for entry type 'database'
                    Property 'keyfile' is not valid for entry type 'database'
                    Property 'location' is not valid for entry type 'database'
                    Property 'phone-number' is not valid for entry type 'database'
                    Property 'pin' is not valid for entry type 'database'
                    Property 'port' is not valid for entry type 'database'
                    Property 'url' is not valid for entry type 'database'
                    """))

    def test_add_door(self):
        """Check that a door entry can be added to a database."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new door entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'door',
                '--description', 'E1 description', '--notes', 'E1 notes',
                '--location', 'E1 location', '--code', 'E1 code', 'E1 name'
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="door">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="generic-location">E1 location</field>
                    \t\t<field id="generic-code">E1 code</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_door_options(self):
        """Check rejection of invalid options for the door type."""
        # Try to add a new door entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'door',
                '--card-number', 'E1 card number', '--card-type',
                'E1 card type', '--ccv', 'E1 CCV', '--certificate',
                'E1 certificate', '--code', 'E1 code', '--database',
                'E1 database', '--domain', 'E1 domain', '--email', 'E1 email',
                '--expiry-date', 'E1 expiry date', '--hostname', 'E1 hostname',
                '--keyfile', 'E1 keyfile', '--location', 'E1 location',
                '--password', '--phone-number', 'E1 phone number', '--pin',
                'E1 PIN', '--port', 'E1 port', '--url', 'E1 URL', '--username',
                'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'card-number' is not valid for entry type 'door'
                    Property 'card-type' is not valid for entry type 'door'
                    Property 'ccv' is not valid for entry type 'door'
                    Property 'certificate' is not valid for entry type 'door'
                    Property 'database' is not valid for entry type 'door'
                    Property 'domain' is not valid for entry type 'door'
                    Property 'email' is not valid for entry type 'door'
                    Property 'expiry-date' is not valid for entry type 'door'
                    Property 'hostname' is not valid for entry type 'door'
                    Property 'keyfile' is not valid for entry type 'door'
                    Property 'password' is not valid for entry type 'door'
                    Property 'phone-number' is not valid for entry type 'door'
                    Property 'pin' is not valid for entry type 'door'
                    Property 'port' is not valid for entry type 'door'
                    Property 'url' is not valid for entry type 'door'
                    Property 'username' is not valid for entry type 'door'
                    """))

    def test_add_email(self):
        """Check that an email entry can be added to a database."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new email entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'email',
                '--description', 'E1 description', '--notes', 'E1 notes',
                '--email', 'E1 email', '--hostname', 'E1 hostname',
                '--username', 'E1 username', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1 password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="email">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="generic-email">E1 email</field>
                    \t\t<field id="generic-hostname">E1 hostname</field>
                    \t\t<field id="generic-username">E1 username</field>
                    \t\t<field id="generic-password">E1 password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_email_options(self):
        """Check rejection of invalid options for the email type."""
        # Try to add a new email entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'email',
                '--card-number', 'E1 card number', '--card-type',
                'E1 card type', '--ccv', 'E1 CCV', '--certificate',
                'E1 certificate', '--code', 'E1 code', '--database',
                'E1 database', '--domain', 'E1 domain', '--email', 'E1 email',
                '--expiry-date', 'E1 expiry date', '--hostname', 'E1 hostname',
                '--keyfile', 'E1 keyfile', '--location', 'E1 location',
                '--password', '--phone-number', 'E1 phone number', '--pin',
                'E1 PIN', '--port', 'E1 port', '--url', 'E1 URL', '--username',
                'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'card-number' is not valid for entry type 'email'
                    Property 'card-type' is not valid for entry type 'email'
                    Property 'ccv' is not valid for entry type 'email'
                    Property 'certificate' is not valid for entry type 'email'
                    Property 'code' is not valid for entry type 'email'
                    Property 'database' is not valid for entry type 'email'
                    Property 'domain' is not valid for entry type 'email'
                    Property 'expiry-date' is not valid for entry type 'email'
                    Property 'keyfile' is not valid for entry type 'email'
                    Property 'location' is not valid for entry type 'email'
                    Property 'phone-number' is not valid for entry type 'email'
                    Property 'pin' is not valid for entry type 'email'
                    Property 'port' is not valid for entry type 'email'
                    Property 'url' is not valid for entry type 'email'
                    """))

    def test_add_ftp(self):
        """Check that an FTP entry can be added to a database."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new FTP entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'ftp',
                '--description', 'E1 description', '--notes', 'E1 notes',
                '--hostname', 'E1 hostname', '--port', 'E1 port', '--username',
                'E1 username', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1 password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="ftp">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="generic-hostname">E1 hostname</field>
                    \t\t<field id="generic-port">E1 port</field>
                    \t\t<field id="generic-username">E1 username</field>
                    \t\t<field id="generic-password">E1 password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_ftp_options(self):
        """Check rejection of invalid options for the FTP type."""
        # Try to add a new FTP entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'ftp',
                '--card-number', 'E1 card number', '--card-type',
                'E1 card type', '--ccv', 'E1 CCV', '--certificate',
                'E1 certificate', '--code', 'E1 code', '--database',
                'E1 database', '--domain', 'E1 domain', '--email', 'E1 email',
                '--expiry-date', 'E1 expiry date', '--hostname', 'E1 hostname',
                '--keyfile', 'E1 keyfile', '--location', 'E1 location',
                '--password', '--phone-number', 'E1 phone number', '--pin',
                'E1 PIN', '--port', 'E1 port', '--url', 'E1 URL', '--username',
                'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'card-number' is not valid for entry type 'ftp'
                    Property 'card-type' is not valid for entry type 'ftp'
                    Property 'ccv' is not valid for entry type 'ftp'
                    Property 'certificate' is not valid for entry type 'ftp'
                    Property 'code' is not valid for entry type 'ftp'
                    Property 'database' is not valid for entry type 'ftp'
                    Property 'domain' is not valid for entry type 'ftp'
                    Property 'email' is not valid for entry type 'ftp'
                    Property 'expiry-date' is not valid for entry type 'ftp'
                    Property 'keyfile' is not valid for entry type 'ftp'
                    Property 'location' is not valid for entry type 'ftp'
                    Property 'phone-number' is not valid for entry type 'ftp'
                    Property 'pin' is not valid for entry type 'ftp'
                    Property 'url' is not valid for entry type 'ftp'
                    """))

    def test_add_generic(self):
        """Check that a generic entry can be added to a database."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new generic entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--description',
                'E1 description', '--notes', 'E1 notes', '--hostname',
                'E1 hostname', '--username', 'E1 username', '--password',
                'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1 password']
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
                utils.dedent("""\
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

    def test_add_generic_options(self):
        """Check rejection of invalid options for the generic type."""
        # Try to add a new generic entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'generic',
                '--card-number', 'E1 card number', '--card-type',
                'E1 card type', '--ccv', 'E1 CCV', '--certificate',
                'E1 certificate', '--code', 'E1 code', '--database',
                'E1 database', '--domain', 'E1 domain', '--email', 'E1 email',
                '--expiry-date', 'E1 expiry date', '--hostname', 'E1 hostname',
                '--keyfile', 'E1 keyfile', '--location', 'E1 location',
                '--password', '--phone-number', 'E1 phone number', '--pin',
                'E1 PIN', '--port', 'E1 port', '--url', 'E1 URL', '--username',
                'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'card-number' is not valid for entry type 'generic'
                    Property 'card-type' is not valid for entry type 'generic'
                    Property 'ccv' is not valid for entry type 'generic'
                    Property 'certificate' is not valid for entry type 'generic'
                    Property 'code' is not valid for entry type 'generic'
                    Property 'database' is not valid for entry type 'generic'
                    Property 'domain' is not valid for entry type 'generic'
                    Property 'email' is not valid for entry type 'generic'
                    Property 'expiry-date' is not valid for entry type 'generic'
                    Property 'keyfile' is not valid for entry type 'generic'
                    Property 'location' is not valid for entry type 'generic'
                    Property 'phone-number' is not valid for entry type 'generic'
                    Property 'pin' is not valid for entry type 'generic'
                    Property 'port' is not valid for entry type 'generic'
                    Property 'url' is not valid for entry type 'generic'
                    """))

    def test_add_phone(self):
        """Check that a phone entry can be added to a database."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new phone entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'phone',
                '--description', 'E1 description', '--notes', 'E1 notes',
                '--phone-number', 'E1 phone number', '--pin', 'E1 PIN',
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="phone">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="phone-phonenumber">E1 phone number</field>
                    \t\t<field id="generic-pin">E1 PIN</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_phone_options(self):
        """Check rejection of invalid options for the phone type."""
        # Try to add a new phone entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'phone',
                '--card-number', 'E1 card number', '--card-type',
                'E1 card type', '--ccv', 'E1 CCV', '--certificate',
                'E1 certificate', '--code', 'E1 code', '--database',
                'E1 database', '--domain', 'E1 domain', '--email', 'E1 email',
                '--expiry-date', 'E1 expiry date', '--hostname', 'E1 hostname',
                '--keyfile', 'E1 keyfile', '--location', 'E1 location',
                '--password', '--phone-number', 'E1 phone number', '--pin',
                'E1 PIN', '--port', 'E1 port', '--url', 'E1 URL', '--username',
                'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'card-number' is not valid for entry type 'phone'
                    Property 'card-type' is not valid for entry type 'phone'
                    Property 'ccv' is not valid for entry type 'phone'
                    Property 'certificate' is not valid for entry type 'phone'
                    Property 'code' is not valid for entry type 'phone'
                    Property 'database' is not valid for entry type 'phone'
                    Property 'domain' is not valid for entry type 'phone'
                    Property 'email' is not valid for entry type 'phone'
                    Property 'expiry-date' is not valid for entry type 'phone'
                    Property 'hostname' is not valid for entry type 'phone'
                    Property 'keyfile' is not valid for entry type 'phone'
                    Property 'location' is not valid for entry type 'phone'
                    Property 'password' is not valid for entry type 'phone'
                    Property 'port' is not valid for entry type 'phone'
                    Property 'url' is not valid for entry type 'phone'
                    Property 'username' is not valid for entry type 'phone'
                    """))

    def test_add_remote_desktop(self):
        """Check that a remote-desktop entry can be added to a database."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new remote-desktop entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type',
                'remote-desktop', '--description', 'E1 description', '--notes',
                'E1 notes', '--hostname', 'E1 hostname', '--port', 'E1 port',
                '--username', 'E1 username', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1 password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="remotedesktop">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="generic-hostname">E1 hostname</field>
                    \t\t<field id="generic-port">E1 port</field>
                    \t\t<field id="generic-username">E1 username</field>
                    \t\t<field id="generic-password">E1 password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_remote_desktop_options(self):
        """Check rejection of invalid options for the remote-desktop type."""
        # Try to add a new remote-desktop entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type',
                'remote-desktop', '--card-number', 'E1 card number',
                '--card-type', 'E1 card type', '--ccv', 'E1 CCV',
                '--certificate', 'E1 certificate', '--code', 'E1 code',
                '--database', 'E1 database', '--domain', 'E1 domain',
                '--email', 'E1 email', '--expiry-date', 'E1 expiry date',
                '--hostname', 'E1 hostname', '--keyfile', 'E1 keyfile',
                '--location', 'E1 location', '--password', '--phone-number',
                'E1 phone number', '--pin', 'E1 PIN', '--port', 'E1 port',
                '--url', 'E1 URL', '--username', 'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'card-number' is not valid for entry type 'remote-desktop'
                    Property 'card-type' is not valid for entry type 'remote-desktop'
                    Property 'ccv' is not valid for entry type 'remote-desktop'
                    Property 'certificate' is not valid for entry type 'remote-desktop'
                    Property 'code' is not valid for entry type 'remote-desktop'
                    Property 'database' is not valid for entry type 'remote-desktop'
                    Property 'domain' is not valid for entry type 'remote-desktop'
                    Property 'email' is not valid for entry type 'remote-desktop'
                    Property 'expiry-date' is not valid for entry type 'remote-desktop'
                    Property 'keyfile' is not valid for entry type 'remote-desktop'
                    Property 'location' is not valid for entry type 'remote-desktop'
                    Property 'phone-number' is not valid for entry type 'remote-desktop'
                    Property 'pin' is not valid for entry type 'remote-desktop'
                    Property 'url' is not valid for entry type 'remote-desktop'
                    """))

    def test_add_shell(self):
        """Check that a shell entry can be added to a database."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new shell entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'shell',
                '--description', 'E1 description', '--notes', 'E1 notes',
                '--hostname', 'E1 hostname', '--domain', 'E1 domain',
                '--username', 'E1 username', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1 password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="shell">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="generic-hostname">E1 hostname</field>
                    \t\t<field id="generic-domain">E1 domain</field>
                    \t\t<field id="generic-username">E1 username</field>
                    \t\t<field id="generic-password">E1 password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_shell_options(self):
        """Check rejection of invalid options for the shell type."""
        # Try to add a new shell entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'shell',
                '--card-number', 'E1 card number', '--card-type',
                'E1 card type', '--ccv', 'E1 CCV', '--certificate',
                'E1 certificate', '--code', 'E1 code', '--database',
                'E1 database', '--domain', 'E1 domain', '--email', 'E1 email',
                '--expiry-date', 'E1 expiry date', '--hostname', 'E1 hostname',
                '--keyfile', 'E1 keyfile', '--location', 'E1 location',
                '--password', '--phone-number', 'E1 phone number', '--pin',
                'E1 PIN', '--port', 'E1 port', '--url', 'E1 URL', '--username',
                'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'card-number' is not valid for entry type 'shell'
                    Property 'card-type' is not valid for entry type 'shell'
                    Property 'ccv' is not valid for entry type 'shell'
                    Property 'certificate' is not valid for entry type 'shell'
                    Property 'code' is not valid for entry type 'shell'
                    Property 'database' is not valid for entry type 'shell'
                    Property 'email' is not valid for entry type 'shell'
                    Property 'expiry-date' is not valid for entry type 'shell'
                    Property 'keyfile' is not valid for entry type 'shell'
                    Property 'location' is not valid for entry type 'shell'
                    Property 'phone-number' is not valid for entry type 'shell'
                    Property 'pin' is not valid for entry type 'shell'
                    Property 'port' is not valid for entry type 'shell'
                    Property 'url' is not valid for entry type 'shell'
                    """))

    def test_add_vnc(self):
        """Check that a VNC entry can be added to a database."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new VNC entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'vnc',
                '--description', 'E1 description', '--notes', 'E1 notes',
                '--hostname', 'E1 hostname', '--port', 'E1 port', '--username',
                'E1 username', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1 password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="vnc">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="generic-hostname">E1 hostname</field>
                    \t\t<field id="generic-port">E1 port</field>
                    \t\t<field id="generic-username">E1 username</field>
                    \t\t<field id="generic-password">E1 password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_vnc_options(self):
        """Check rejection of invalid options for the VNC type."""
        # Try to add a new VNC entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'vnc',
                '--card-number', 'E1 card number', '--card-type',
                'E1 card type', '--ccv', 'E1 CCV', '--certificate',
                'E1 certificate', '--code', 'E1 code', '--database',
                'E1 database', '--domain', 'E1 domain', '--email', 'E1 email',
                '--expiry-date', 'E1 expiry date', '--hostname', 'E1 hostname',
                '--keyfile', 'E1 keyfile', '--location', 'E1 location',
                '--password', '--phone-number', 'E1 phone number', '--pin',
                'E1 PIN', '--port', 'E1 port', '--url', 'E1 URL', '--username',
                'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'card-number' is not valid for entry type 'vnc'
                    Property 'card-type' is not valid for entry type 'vnc'
                    Property 'ccv' is not valid for entry type 'vnc'
                    Property 'certificate' is not valid for entry type 'vnc'
                    Property 'code' is not valid for entry type 'vnc'
                    Property 'database' is not valid for entry type 'vnc'
                    Property 'domain' is not valid for entry type 'vnc'
                    Property 'email' is not valid for entry type 'vnc'
                    Property 'expiry-date' is not valid for entry type 'vnc'
                    Property 'keyfile' is not valid for entry type 'vnc'
                    Property 'location' is not valid for entry type 'vnc'
                    Property 'phone-number' is not valid for entry type 'vnc'
                    Property 'pin' is not valid for entry type 'vnc'
                    Property 'url' is not valid for entry type 'vnc'
                    """))

    def test_add_website(self):
        """Check that a website entry can be added to a database."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Add a new website entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'website',
                '--description', 'E1 description', '--notes', 'E1 notes',
                '--url', 'E1 URL', '--username', 'E1 username', '--email',
                'E1 email', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1 password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="website">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1 description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1 notes</notes>
                    \t\t<field id="generic-url">E1 URL</field>
                    \t\t<field id="generic-username">E1 username</field>
                    \t\t<field id="generic-email">E1 email</field>
                    \t\t<field id="generic-password">E1 password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_add_website_options(self):
        """Check rejection of invalid options for the website type."""
        # Try to add a new website entry with invalid options.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'add', '--type', 'website',
                '--card-number', 'E1 card number', '--card-type',
                'E1 card type', '--ccv', 'E1 CCV', '--certificate',
                'E1 certificate', '--code', 'E1 code', '--database',
                'E1 database', '--domain', 'E1 domain', '--email', 'E1 email',
                '--expiry-date', 'E1 expiry date', '--hostname', 'E1 hostname',
                '--keyfile', 'E1 keyfile', '--location', 'E1 location',
                '--password', '--phone-number', 'E1 phone number', '--pin',
                'E1 PIN', '--port', 'E1 port', '--url', 'E1 URL', '--username',
                'E1 username', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'card-number' is not valid for entry type 'website'
                    Property 'card-type' is not valid for entry type 'website'
                    Property 'ccv' is not valid for entry type 'website'
                    Property 'certificate' is not valid for entry type 'website'
                    Property 'code' is not valid for entry type 'website'
                    Property 'database' is not valid for entry type 'website'
                    Property 'domain' is not valid for entry type 'website'
                    Property 'expiry-date' is not valid for entry type 'website'
                    Property 'hostname' is not valid for entry type 'website'
                    Property 'keyfile' is not valid for entry type 'website'
                    Property 'location' is not valid for entry type 'website'
                    Property 'phone-number' is not valid for entry type 'website'
                    Property 'pin' is not valid for entry type 'website'
                    Property 'port' is not valid for entry type 'website'
                    """))

    def test_edit(self):
        """Check that a single entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="generic">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', 'E1 name'
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="generic">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_invalid_path(self):
        """Check rejection to edit a non-existent entry."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Try to edit a nested generic entry with an invalid path.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'edit',
             'E1 name/E2 name']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Entry 'E1 name' (element #1 in 'E1 name/E2 name') does not exist
                    """))

    def test_edit_reset(self):
        """Check that an entry property can be fully cleaned in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                '', '--notes', '', '--username', '', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, '']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="generic">
                    \t\t<name>E1 name</name>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<field id="generic-hostname">E1 hostname</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_type(self):
        """Check that a type of an entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="generic">
                \t\t<name>E1 name</name>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-password">E1 password</field>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry from 'generic' to 'website':
        # * Property 'hostname' should be removed because it is not valid for
        #   the target type.
        # * Property 'url', which is valid only for the target type, should be
        #   set to a value specified on the command line.
        # * Common property 'username' should be updated to a value specified
        #   on the command line.
        # * Common property 'password' should be left unchanged because no new
        #   value is specified on the command line.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--type',
                'website', '--url', 'E1-U URL', '--username', 'E1-U username',
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="website">
                    \t\t<name>E1 name</name>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<field id="generic-url">E1-U URL</field>
                    \t\t<field id="generic-username">E1-U username</field>
                    \t\t<field id="generic-password">E1 password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_type_options(self):
        """Check rejection of invalid options when changing an entry type."""
        # Create a new empty password database.
        self._init_database(self.dbname)

        # Check that trying to change a type of an entry and using an invalid
        # option for a given type results in an early error.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--type', 'folder',
                '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Property 'password' is not valid for entry type 'folder'
                    """))

    def test_edit_type_empty_folder(self):
        """Check that an empty folder can be changed to a different type."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<name>E1 name</name>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--type',
                'generic', '--hostname', 'E1-U hostname', 'E1 name'
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="generic">
                    \t\t<name>E1 name</name>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<field id="generic-hostname">E1-U hostname</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_type_non_empty_folder(self):
        """Check rejection of changing a non-empty folder to another type."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<name>E1 name</name>
                \t\t<entry type="generic">
                \t\t\t<name>E2 name</name>
                \t\t</entry>
                \t</entry>
                </revelationdata>
                '''))

        # Try to edit the top folder.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--type',
                'generic', '--hostname', 'E1-U hostname', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 1)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(cli_mock.stdout.getvalue(), "")
            self.assertEqual(
                cli_mock.stderr.getvalue(),
                utils.dedent("""\
                    Entry 'E1 name' is not empty and cannot be replaced by a non-folder type
                    """))

    def test_edit_folder(self):
        """Check that a folder entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="folder">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<notes>E1 notes</notes>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', 'E1 name'
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="folder">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_credit_card(self):
        """Check that a credit-card entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="creditcard">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="creditcard-cardtype">E1 card type</field>
                \t\t<field id="creditcard-cardnumber">E1 card number</field>
                \t\t<field id="creditcard-expirydate">E1 expiry date</field>
                \t\t<field id="creditcard-ccv">E1 CCV</field>
                \t\t<field id="generic-pin">E1 PIN</field>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', '--card-type',
                'E1-U card type', '--card-number', 'E1-U card number',
                '--expiry-date', 'E1-U expiry date', '--ccv', 'E1-U CCV',
                '--pin', 'E1-U PIN', 'E1 name'
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="creditcard">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t\t<field id="creditcard-cardtype">E1-U card type</field>
                    \t\t<field id="creditcard-cardnumber">E1-U card number</field>
                    \t\t<field id="creditcard-expirydate">E1-U expiry date</field>
                    \t\t<field id="creditcard-ccv">E1-U CCV</field>
                    \t\t<field id="generic-pin">E1-U PIN</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_crypto_key(self):
        """Check that a crypto-key entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="cryptokey">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-certificate">E1 certificate</field>
                \t\t<field id="generic-keyfile">E1 keyfile</field>
                \t\t<field id="generic-password">E1 password</field>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', '--hostname',
                'E1-U hostname', '--certificate', 'E1-U certificate',
                '--keyfile', 'E1-U keyfile', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1-U password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="cryptokey">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t\t<field id="generic-hostname">E1-U hostname</field>
                    \t\t<field id="generic-certificate">E1-U certificate</field>
                    \t\t<field id="generic-keyfile">E1-U keyfile</field>
                    \t\t<field id="generic-password">E1-U password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_database(self):
        """Check that a database entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="database">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-password">E1 password</field>
                \t\t<field id="generic-database">E1 database</field>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', '--hostname',
                'E1-U hostname', '--username', 'E1-U username', '--password',
                '--database', 'E1-U database', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1-U password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="database">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t\t<field id="generic-hostname">E1-U hostname</field>
                    \t\t<field id="generic-username">E1-U username</field>
                    \t\t<field id="generic-password">E1-U password</field>
                    \t\t<field id="generic-database">E1-U database</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_door(self):
        """Check that a door entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="door">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-location">E1 location</field>
                \t\t<field id="generic-code">E1 code</field>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', '--location',
                'E1-U location', '--code', 'E1-U code', 'E1 name'
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="door">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t\t<field id="generic-location">E1-U location</field>
                    \t\t<field id="generic-code">E1-U code</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_email(self):
        """Check that an email entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="email">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-email">E1 email</field>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-password">E1 password</field>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', '--email',
                'E1-U email', '--hostname', 'E1-U hostname', '--username',
                'E1-U username', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1-U password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="email">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t\t<field id="generic-email">E1-U email</field>
                    \t\t<field id="generic-hostname">E1-U hostname</field>
                    \t\t<field id="generic-username">E1-U username</field>
                    \t\t<field id="generic-password">E1-U password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_ftp(self):
        """Check that an FTP entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="ftp">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-port">E1 port</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-password">E1 password</field>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', '--hostname',
                'E1-U hostname', '--port', 'E1-U port', '--username',
                'E1-U username', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1-U password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="ftp">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t\t<field id="generic-hostname">E1-U hostname</field>
                    \t\t<field id="generic-port">E1-U port</field>
                    \t\t<field id="generic-username">E1-U username</field>
                    \t\t<field id="generic-password">E1-U password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_generic(self):
        """Check that a generic entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', '--hostname',
                'E1-U hostname', '--username', 'E1-U username', '--password',
                'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1-U password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="generic">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t\t<field id="generic-hostname">E1-U hostname</field>
                    \t\t<field id="generic-username">E1-U username</field>
                    \t\t<field id="generic-password">E1-U password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_phone(self):
        """Check that a phone entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="phone">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="phone-phonenumber">E1 phone number</field>
                \t\t<field id="generic-pin">E1 pin</field>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', '--phone-number',
                'E1-U phone number', '--pin', 'E1-U PIN', 'E1 name'
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="phone">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t\t<field id="phone-phonenumber">E1-U phone number</field>
                    \t\t<field id="generic-pin">E1-U PIN</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_remote_desktop(self):
        """Check that a remote-desktop entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="remotedesktop">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-port">E1 port</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-password">E1 password</field>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', '--hostname',
                'E1-U hostname', '--port', 'E1-U port', '--username',
                'E1-U username', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1-U password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="remotedesktop">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t\t<field id="generic-hostname">E1-U hostname</field>
                    \t\t<field id="generic-port">E1-U port</field>
                    \t\t<field id="generic-username">E1-U username</field>
                    \t\t<field id="generic-password">E1-U password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_shell(self):
        """Check that a shell entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="shell">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-domain">E1 domain</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-password">E1 password</field>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', '--hostname',
                'E1-U hostname', '--domain', 'E1-U domain', '--username',
                'E1-U username', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1-U password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="shell">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t\t<field id="generic-hostname">E1-U hostname</field>
                    \t\t<field id="generic-domain">E1-U domain</field>
                    \t\t<field id="generic-username">E1-U username</field>
                    \t\t<field id="generic-password">E1-U password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_vnc(self):
        """Check that a VNC entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="vnc">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-port">E1 port</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-password">E1 password</field>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', '--hostname',
                'E1-U hostname', '--port', 'E1-U port', '--username',
                'E1-U username', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1-U password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="vnc">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t\t<field id="generic-hostname">E1-U hostname</field>
                    \t\t<field id="generic-port">E1-U port</field>
                    \t\t<field id="generic-username">E1-U username</field>
                    \t\t<field id="generic-password">E1-U password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_edit_website(self):
        """Check that a website entry can be edited in a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="website">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-url">E1 URL</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-email">E1 email</field>
                \t\t<field id="generic-password">E1 password</field>
                \t</entry>
                </revelationdata>
                '''))

        # Edit the entry.
        with cli_context([
                'storepass-cli', '-f', self.dbname, 'edit', '--description',
                'E1-U description', '--notes', 'E1-U notes', '--url',
                'E1-U URL', '--username', 'E1-U username', '--email',
                'E1-U email', '--password', 'E1 name'
        ]) as cli_mock:
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD, 'E1-U password']
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
                utils.dedent("""\
                    ^<\\?xml version='1\\.0' encoding='UTF-8'\\?>
                    <revelationdata dataversion="1">
                    \t<entry type="website">
                    \t\t<name>E1 name</name>
                    \t\t<description>E1-U description</description>
                    \t\t<updated>[0-9]+</updated>
                    \t\t<notes>E1-U notes</notes>
                    \t\t<field id="generic-url">E1-U URL</field>
                    \t\t<field id="generic-username">E1-U username</field>
                    \t\t<field id="generic-email">E1-U email</field>
                    \t\t<field id="generic-password">E1-U password</field>
                    \t</entry>
                    </revelationdata>
                    $"""))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_delete(self):
        """Check that an entry can be deleted from a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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
                utils.dedent("""\
                    <?xml version='1.0' encoding='UTF-8'?>
                    <revelationdata dataversion="1" />
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_delete_nested(self):
        """Check that nested entries can be deleted from a database."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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
                utils.dedent("""\
                    <?xml version='1.0' encoding='UTF-8'?>
                    <revelationdata dataversion="1">
                    \t<entry type="folder">
                    \t\t<name>E1 name</name>
                    \t</entry>
                    </revelationdata>
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_delete_invalid_path(self):
        """Check rejection to delete a non-existent entry."""
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
                utils.dedent("""\
                    Entry 'E1 name' (element #1 in 'E1 name/E2 name') does not exist
                    """))

    def test_delete_non_empty(self):
        """Check rejection to delete a non-empty folder."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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
                utils.dedent("""\
                    Entry 'E1 name' is not empty and cannot be removed
                    """))

    def test_list(self):
        """Check that a single entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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
                utils.dedent("""\
                    - E1 name
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_nested(self):
        """Check that nested entries are listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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
                utils.dedent2("""\
                    |+ E1 name
                    |  + E2 name
                    |    - E3 name
                    |+ E4 name
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_folder(self):
        """Check that a folder entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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
                utils.dedent("""\
                    + E1 name: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_credit_card(self):
        """Check that a credit-card entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="creditcard">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="creditcard-cardtype">E1 card type</field>
                \t\t<field id="creditcard-cardnumber">E1 card number</field>
                \t\t<field id="creditcard-expirydate">E1 expiry date</field>
                \t\t<field id="creditcard-ccv">E1 CCV</field>
                \t\t<field id="generic-pin">E1 PIN</field>
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
                utils.dedent("""\
                    - E1 name: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_crypto_key(self):
        """Check that a crypto-key entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="cryptokey">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-certificate">E1 certificate</field>
                \t\t<field id="generic-keyfile">E1 keyfile</field>
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
                utils.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_database(self):
        """Check that a database entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="database">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-password">E1 password</field>
                \t\t<field id="generic-database">E1 database</field>
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
                utils.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_door(self):
        """Check that a door entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="door">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-location">E1 location</field>
                \t\t<field id="generic-code">E1 code</field>
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
                utils.dedent("""\
                    - E1 name: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_email(self):
        """Check that an email entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="email">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-email">E1 email</field>
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
                utils.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_ftp(self):
        """Check that an FTP entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="ftp">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-port">E1 port</field>
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
                utils.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_generic(self):
        """Check that a generic entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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
                utils.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_phone(self):
        """Check that a phone entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="phone">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="phone-phonenumber">E1 phone number</field>
                \t\t<field id="generic-pin">E1 PIN</field>
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
                utils.dedent("""\
                    - E1 name: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_remote_desktop(self):
        """Check that a remote-desktop entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="remotedesktop">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-port">E1 port</field>
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
                utils.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_shell(self):
        """Check that a shell entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="shell">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-domain">E1 domain</field>
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
                utils.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_vnc(self):
        """Check that a VNC entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="vnc">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-port">E1 port</field>
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
                utils.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_website(self):
        """Check that a website entry is listed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="website">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-url">E1 URL</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-email">E1 email</field>
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
                utils.dedent("""\
                    - E1 name [E1 URL]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show(self):
        """Check that details of a single entry are displayed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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
                utils.dedent("""\
                    + E1 name (Generic)
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_timezone(self):
        """Check that a date of the last change uses a configured timezone."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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
                utils.dedent2("""\
                    |+ E1 name (Generic)
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

        # Check the display with the GMT-1 timezone.
        with cli_context(
            ['storepass-cli', '-f', self.dbname, 'show', 'E1 name'],
                timezone='GMT-1') as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_called_once()
            self.assertEqual(
                cli_mock.stdout.getvalue(),
                utils.dedent2("""\
                    |+ E1 name (Generic)
                    |  - Last modified: Tue Jan  1 01:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_nested(self):
        """Check that nested entries are displayed correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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
                utils.dedent("""\
                    + E1 name (Folder)
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
                utils.dedent("""\
                    + E1 name/E2 name (Folder)
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
                utils.dedent("""\
                    + E1 name/E2 name/E3 name (Generic)
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
                utils.dedent("""\
                    + E4 name (Folder)
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_folder(self):
        """Check that details of a folder entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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
                utils.dedent2("""\
                    |+ E1 name (Folder)
                    |  - Description: E1 description
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_credit_card(self):
        """Check that details of a credit-card entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="creditcard">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="creditcard-cardtype">E1 card type</field>
                \t\t<field id="creditcard-cardnumber">E1 card number</field>
                \t\t<field id="creditcard-expirydate">E1 expiry date</field>
                \t\t<field id="creditcard-ccv">E1 CCV</field>
                \t\t<field id="generic-pin">E1 PIN</field>
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
                utils.dedent2("""\
                    |+ E1 name (Credit card)
                    |  - Description: E1 description
                    |  - Card type: E1 card type
                    |  - Card number: E1 card number
                    |  - Expiry date: E1 expiry date
                    |  - CCV: E1 CCV
                    |  - PIN: E1 PIN
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_crypto_key(self):
        """Check that details of a crypto-key entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="cryptokey">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-certificate">E1 certificate</field>
                \t\t<field id="generic-keyfile">E1 keyfile</field>
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
                utils.dedent2("""\
                    |+ E1 name (Crypto key)
                    |  - Description: E1 description
                    |  - Hostname: E1 hostname
                    |  - Certificate: E1 certificate
                    |  - Keyfile: E1 keyfile
                    |  - Password: E1 password
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_database(self):
        """Check that details of a database entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="database">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-password">E1 password</field>
                \t\t<field id="generic-database">E1 database</field>
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
                utils.dedent2("""\
                    |+ E1 name (Database)
                    |  - Description: E1 description
                    |  - Hostname: E1 hostname
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Database: E1 database
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_door(self):
        """Check that details of a door entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="door">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-location">E1 location</field>
                \t\t<field id="generic-code">E1 code</field>
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
                utils.dedent2("""\
                    |+ E1 name (Door)
                    |  - Description: E1 description
                    |  - Location: E1 location
                    |  - Code: E1 code
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_email(self):
        """Check that details of an email entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="email">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-email">E1 email</field>
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
                utils.dedent2("""\
                    |+ E1 name (Email)
                    |  - Description: E1 description
                    |  - Email: E1 email
                    |  - Hostname: E1 hostname
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_ftp(self):
        """Check that details of an FTP entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="ftp">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-port">E1 port</field>
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
                utils.dedent2("""\
                    |+ E1 name (FTP)
                    |  - Description: E1 description
                    |  - Hostname: E1 hostname
                    |  - Port: E1 port
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_generic(self):
        """Check that details of a generic entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
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
                utils.dedent2("""\
                    |+ E1 name (Generic)
                    |  - Description: E1 description
                    |  - Hostname: E1 hostname
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_phone(self):
        """Check that details of a phone entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="phone">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="phone-phonenumber">E1 phone number</field>
                \t\t<field id="generic-pin">E1 PIN</field>
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
                utils.dedent2("""\
                    |+ E1 name (Phone)
                    |  - Description: E1 description
                    |  - Phone number: E1 phone number
                    |  - PIN: E1 PIN
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_remote_desktop(self):
        """Check that details of a remote-desktop entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="remotedesktop">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-port">E1 port</field>
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
                utils.dedent2("""\
                    |+ E1 name (Remote desktop)
                    |  - Description: E1 description
                    |  - Hostname: E1 hostname
                    |  - Port: E1 port
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_shell(self):
        """Check that details of a shell entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="shell">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-domain">E1 domain</field>
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
                utils.dedent2("""\
                    |+ E1 name (Shell)
                    |  - Description: E1 description
                    |  - Hostname: E1 hostname
                    |  - Domain: E1 domain
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_vnc(self):
        """Check that details of a VNC entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="vnc">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-hostname">E1 hostname</field>
                \t\t<field id="generic-port">E1 port</field>
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
                utils.dedent2("""\
                    |+ E1 name (VNC)
                    |  - Description: E1 description
                    |  - Hostname: E1 hostname
                    |  - Port: E1 port
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_website(self):
        """Check that details of a website entry are shown correctly."""
        # Create a test database.
        utils.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            utils.dedent('''\
                <revelationdata dataversion="1">
                \t<entry type="website">
                \t\t<name>E1 name</name>
                \t\t<description>E1 description</description>
                \t\t<updated>1546300800</updated>
                \t\t<notes>E1 notes</notes>
                \t\t<field id="generic-url">E1 URL</field>
                \t\t<field id="generic-username">E1 username</field>
                \t\t<field id="generic-email">E1 email</field>
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
                utils.dedent2("""\
                    |+ E1 name (Website)
                    |  - Description: E1 description
                    |  - URL: E1 URL
                    |  - Username: E1 username
                    |  - Email: E1 email
                    |  - Password: E1 password
                    |  - Notes: E1 notes
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")
