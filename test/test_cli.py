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


class TestCLI(util.StorePassTestCase):
    """End-to-end command line tests."""
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
                util.dedent2("""\
                    |usage: storepass-cli add [-h]
                    |                         [--type {folder,credit-card,crypto-key,database,door,email,ftp,generic,phone,shell,remote-desktop,vnc,website}]
                    |                         [--description DESC] [--notes NOTES]
                    |                         [--card-number ID] [--card-type TYPE] [--ccv CCV]
                    |                         [--certificate CERT] [--code CODE] [--database NAME]
                    |                         [--domain NAME] [--email ADDRESS]
                    |                         [--expiry-date DATE] [--hostname HOST]
                    |                         [--keyfile FILE] [--location PLACE] [--password]
                    |                         [--phone-number PHONE] [--pin PIN] [--port NUMBER]
                    |                         [--url ADDRESS] [--username USER]
                    |                         ENTRY
                    |
                    |add a new password entry
                    |
                    |positional arguments:
                    |  ENTRY                 password entry
                    |
                    |optional arguments:
                    |  -h, --help            show this help message and exit
                    |  --type {folder,credit-card,crypto-key,database,door,email,ftp,generic,phone,shell,remote-desktop,vnc,website}
                    |                        entry type (the default is generic)
                    |
                    |optional arguments valid for all entry types:
                    |  --description DESC    set entry description to the specified value
                    |  --notes NOTES         set entry notes to the specified value
                    |
                    |optional arguments valid for specific account types:
                    |  --card-number ID      set card number to the specified value
                    |  --card-type TYPE      set card type to the specified value
                    |  --ccv CCV             set CCV number to the specified value
                    |  --certificate CERT    set certificate to the specified value
                    |  --code CODE           set code to the specified value
                    |  --database NAME       set database name to the specified value
                    |  --domain NAME         set domain name to the specified value
                    |  --email ADDRESS       set email to the specified value
                    |  --expiry-date DATE    set expiry date to the specified value
                    |  --hostname HOST       set hostname to the specified value
                    |  --keyfile FILE        set keyfile to the specified value
                    |  --location PLACE      set location to the specified value
                    |  --password            prompt for a password value
                    |  --phone-number PHONE  set phone number to the specified value
                    |  --pin PIN             set PIN to the specified value
                    |  --port NUMBER         set port to the specified value
                    |  --url ADDRESS         set URL to the specified value
                    |  --username USER       set username to the specified value
                    |
                    |option validity for account types:
                    |  credit-card:          card-type, card-number, expiry-date, ccv, pin
                    |  crypto-key:           hostname, certificate, keyfile, password
                    |  database:             hostname, username, password, database
                    |  door:                 location, code
                    |  email:                email, hostname, username, password
                    |  ftp:                  hostname, port, username, password
                    |  generic:              hostname, username, password
                    |  phone:                phone-number, pin
                    |  shell:                hostname, domain, username, password
                    |  remote-desktop:       hostname, port, username, password
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
                util.dedent("""\
                    storepass-cli: error: failed to load password database \'missing.db\': [Errno 2] No such file or directory: \'missing.db\'
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
        """Check that the init command does not overwrite an existing file."""
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
                util.dedent("""\
                    storepass-cli: error: option --card-number is not valid for entry type 'folder'
                    storepass-cli: error: option --card-type is not valid for entry type 'folder'
                    storepass-cli: error: option --ccv is not valid for entry type 'folder'
                    storepass-cli: error: option --certificate is not valid for entry type 'folder'
                    storepass-cli: error: option --code is not valid for entry type 'folder'
                    storepass-cli: error: option --database is not valid for entry type 'folder'
                    storepass-cli: error: option --domain is not valid for entry type 'folder'
                    storepass-cli: error: option --email is not valid for entry type 'folder'
                    storepass-cli: error: option --expiry-date is not valid for entry type 'folder'
                    storepass-cli: error: option --hostname is not valid for entry type 'folder'
                    storepass-cli: error: option --keyfile is not valid for entry type 'folder'
                    storepass-cli: error: option --location is not valid for entry type 'folder'
                    storepass-cli: error: option --password is not valid for entry type 'folder'
                    storepass-cli: error: option --phone-number is not valid for entry type 'folder'
                    storepass-cli: error: option --pin is not valid for entry type 'folder'
                    storepass-cli: error: option --port is not valid for entry type 'folder'
                    storepass-cli: error: option --url is not valid for entry type 'folder'
                    storepass-cli: error: option --username is not valid for entry type 'folder'
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
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD]
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            self.assertEqual(cli_mock.getpass.call_count, 1)
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
                util.dedent("""\
                    storepass-cli: error: option --certificate is not valid for entry type 'credit-card'
                    storepass-cli: error: option --code is not valid for entry type 'credit-card'
                    storepass-cli: error: option --database is not valid for entry type 'credit-card'
                    storepass-cli: error: option --domain is not valid for entry type 'credit-card'
                    storepass-cli: error: option --email is not valid for entry type 'credit-card'
                    storepass-cli: error: option --hostname is not valid for entry type 'credit-card'
                    storepass-cli: error: option --keyfile is not valid for entry type 'credit-card'
                    storepass-cli: error: option --location is not valid for entry type 'credit-card'
                    storepass-cli: error: option --password is not valid for entry type 'credit-card'
                    storepass-cli: error: option --phone-number is not valid for entry type 'credit-card'
                    storepass-cli: error: option --port is not valid for entry type 'credit-card'
                    storepass-cli: error: option --url is not valid for entry type 'credit-card'
                    storepass-cli: error: option --username is not valid for entry type 'credit-card'
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
                util.dedent("""\
                    storepass-cli: error: option --card-number is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --card-type is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --ccv is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --code is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --database is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --domain is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --email is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --expiry-date is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --location is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --phone-number is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --pin is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --port is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --url is not valid for entry type 'crypto-key'
                    storepass-cli: error: option --username is not valid for entry type 'crypto-key'
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
                util.dedent("""\
                    storepass-cli: error: option --card-number is not valid for entry type 'database'
                    storepass-cli: error: option --card-type is not valid for entry type 'database'
                    storepass-cli: error: option --ccv is not valid for entry type 'database'
                    storepass-cli: error: option --certificate is not valid for entry type 'database'
                    storepass-cli: error: option --code is not valid for entry type 'database'
                    storepass-cli: error: option --domain is not valid for entry type 'database'
                    storepass-cli: error: option --email is not valid for entry type 'database'
                    storepass-cli: error: option --expiry-date is not valid for entry type 'database'
                    storepass-cli: error: option --keyfile is not valid for entry type 'database'
                    storepass-cli: error: option --location is not valid for entry type 'database'
                    storepass-cli: error: option --phone-number is not valid for entry type 'database'
                    storepass-cli: error: option --pin is not valid for entry type 'database'
                    storepass-cli: error: option --port is not valid for entry type 'database'
                    storepass-cli: error: option --url is not valid for entry type 'database'
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
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD]
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            self.assertEqual(cli_mock.getpass.call_count, 1)
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
                util.dedent("""\
                    storepass-cli: error: option --card-number is not valid for entry type 'door'
                    storepass-cli: error: option --card-type is not valid for entry type 'door'
                    storepass-cli: error: option --ccv is not valid for entry type 'door'
                    storepass-cli: error: option --certificate is not valid for entry type 'door'
                    storepass-cli: error: option --database is not valid for entry type 'door'
                    storepass-cli: error: option --domain is not valid for entry type 'door'
                    storepass-cli: error: option --email is not valid for entry type 'door'
                    storepass-cli: error: option --expiry-date is not valid for entry type 'door'
                    storepass-cli: error: option --hostname is not valid for entry type 'door'
                    storepass-cli: error: option --keyfile is not valid for entry type 'door'
                    storepass-cli: error: option --password is not valid for entry type 'door'
                    storepass-cli: error: option --phone-number is not valid for entry type 'door'
                    storepass-cli: error: option --pin is not valid for entry type 'door'
                    storepass-cli: error: option --port is not valid for entry type 'door'
                    storepass-cli: error: option --url is not valid for entry type 'door'
                    storepass-cli: error: option --username is not valid for entry type 'door'
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
                util.dedent("""\
                    storepass-cli: error: option --card-number is not valid for entry type 'email'
                    storepass-cli: error: option --card-type is not valid for entry type 'email'
                    storepass-cli: error: option --ccv is not valid for entry type 'email'
                    storepass-cli: error: option --certificate is not valid for entry type 'email'
                    storepass-cli: error: option --code is not valid for entry type 'email'
                    storepass-cli: error: option --database is not valid for entry type 'email'
                    storepass-cli: error: option --domain is not valid for entry type 'email'
                    storepass-cli: error: option --expiry-date is not valid for entry type 'email'
                    storepass-cli: error: option --keyfile is not valid for entry type 'email'
                    storepass-cli: error: option --location is not valid for entry type 'email'
                    storepass-cli: error: option --phone-number is not valid for entry type 'email'
                    storepass-cli: error: option --pin is not valid for entry type 'email'
                    storepass-cli: error: option --port is not valid for entry type 'email'
                    storepass-cli: error: option --url is not valid for entry type 'email'
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
                util.dedent("""\
                    storepass-cli: error: option --card-number is not valid for entry type 'ftp'
                    storepass-cli: error: option --card-type is not valid for entry type 'ftp'
                    storepass-cli: error: option --ccv is not valid for entry type 'ftp'
                    storepass-cli: error: option --certificate is not valid for entry type 'ftp'
                    storepass-cli: error: option --code is not valid for entry type 'ftp'
                    storepass-cli: error: option --database is not valid for entry type 'ftp'
                    storepass-cli: error: option --domain is not valid for entry type 'ftp'
                    storepass-cli: error: option --email is not valid for entry type 'ftp'
                    storepass-cli: error: option --expiry-date is not valid for entry type 'ftp'
                    storepass-cli: error: option --keyfile is not valid for entry type 'ftp'
                    storepass-cli: error: option --location is not valid for entry type 'ftp'
                    storepass-cli: error: option --phone-number is not valid for entry type 'ftp'
                    storepass-cli: error: option --pin is not valid for entry type 'ftp'
                    storepass-cli: error: option --url is not valid for entry type 'ftp'
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
                util.dedent("""\
                    storepass-cli: error: option --card-number is not valid for entry type 'generic'
                    storepass-cli: error: option --card-type is not valid for entry type 'generic'
                    storepass-cli: error: option --ccv is not valid for entry type 'generic'
                    storepass-cli: error: option --certificate is not valid for entry type 'generic'
                    storepass-cli: error: option --code is not valid for entry type 'generic'
                    storepass-cli: error: option --database is not valid for entry type 'generic'
                    storepass-cli: error: option --domain is not valid for entry type 'generic'
                    storepass-cli: error: option --email is not valid for entry type 'generic'
                    storepass-cli: error: option --expiry-date is not valid for entry type 'generic'
                    storepass-cli: error: option --keyfile is not valid for entry type 'generic'
                    storepass-cli: error: option --location is not valid for entry type 'generic'
                    storepass-cli: error: option --phone-number is not valid for entry type 'generic'
                    storepass-cli: error: option --pin is not valid for entry type 'generic'
                    storepass-cli: error: option --port is not valid for entry type 'generic'
                    storepass-cli: error: option --url is not valid for entry type 'generic'
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
            cli_mock.getpass.side_effect = [DEFAULT_PASSWORD]
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            self.assertEqual(cli_mock.getpass.call_count, 1)
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
                util.dedent("""\
                    storepass-cli: error: option --card-number is not valid for entry type 'phone'
                    storepass-cli: error: option --card-type is not valid for entry type 'phone'
                    storepass-cli: error: option --ccv is not valid for entry type 'phone'
                    storepass-cli: error: option --certificate is not valid for entry type 'phone'
                    storepass-cli: error: option --code is not valid for entry type 'phone'
                    storepass-cli: error: option --database is not valid for entry type 'phone'
                    storepass-cli: error: option --domain is not valid for entry type 'phone'
                    storepass-cli: error: option --email is not valid for entry type 'phone'
                    storepass-cli: error: option --expiry-date is not valid for entry type 'phone'
                    storepass-cli: error: option --hostname is not valid for entry type 'phone'
                    storepass-cli: error: option --keyfile is not valid for entry type 'phone'
                    storepass-cli: error: option --location is not valid for entry type 'phone'
                    storepass-cli: error: option --password is not valid for entry type 'phone'
                    storepass-cli: error: option --port is not valid for entry type 'phone'
                    storepass-cli: error: option --url is not valid for entry type 'phone'
                    storepass-cli: error: option --username is not valid for entry type 'phone'
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
                util.dedent("""\
                    storepass-cli: error: option --card-number is not valid for entry type 'shell'
                    storepass-cli: error: option --card-type is not valid for entry type 'shell'
                    storepass-cli: error: option --ccv is not valid for entry type 'shell'
                    storepass-cli: error: option --certificate is not valid for entry type 'shell'
                    storepass-cli: error: option --code is not valid for entry type 'shell'
                    storepass-cli: error: option --database is not valid for entry type 'shell'
                    storepass-cli: error: option --email is not valid for entry type 'shell'
                    storepass-cli: error: option --expiry-date is not valid for entry type 'shell'
                    storepass-cli: error: option --keyfile is not valid for entry type 'shell'
                    storepass-cli: error: option --location is not valid for entry type 'shell'
                    storepass-cli: error: option --phone-number is not valid for entry type 'shell'
                    storepass-cli: error: option --pin is not valid for entry type 'shell'
                    storepass-cli: error: option --port is not valid for entry type 'shell'
                    storepass-cli: error: option --url is not valid for entry type 'shell'
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
                util.dedent("""\
                    storepass-cli: error: option --card-number is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --card-type is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --ccv is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --certificate is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --code is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --database is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --domain is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --email is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --expiry-date is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --keyfile is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --location is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --phone-number is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --pin is not valid for entry type 'remote-desktop'
                    storepass-cli: error: option --url is not valid for entry type 'remote-desktop'
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
                util.dedent("""\
                    storepass-cli: error: option --card-number is not valid for entry type 'vnc'
                    storepass-cli: error: option --card-type is not valid for entry type 'vnc'
                    storepass-cli: error: option --ccv is not valid for entry type 'vnc'
                    storepass-cli: error: option --certificate is not valid for entry type 'vnc'
                    storepass-cli: error: option --code is not valid for entry type 'vnc'
                    storepass-cli: error: option --database is not valid for entry type 'vnc'
                    storepass-cli: error: option --domain is not valid for entry type 'vnc'
                    storepass-cli: error: option --email is not valid for entry type 'vnc'
                    storepass-cli: error: option --expiry-date is not valid for entry type 'vnc'
                    storepass-cli: error: option --keyfile is not valid for entry type 'vnc'
                    storepass-cli: error: option --location is not valid for entry type 'vnc'
                    storepass-cli: error: option --phone-number is not valid for entry type 'vnc'
                    storepass-cli: error: option --pin is not valid for entry type 'vnc'
                    storepass-cli: error: option --url is not valid for entry type 'vnc'
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
                util.dedent("""\
                    storepass-cli: error: option --card-number is not valid for entry type 'website'
                    storepass-cli: error: option --card-type is not valid for entry type 'website'
                    storepass-cli: error: option --ccv is not valid for entry type 'website'
                    storepass-cli: error: option --certificate is not valid for entry type 'website'
                    storepass-cli: error: option --code is not valid for entry type 'website'
                    storepass-cli: error: option --database is not valid for entry type 'website'
                    storepass-cli: error: option --domain is not valid for entry type 'website'
                    storepass-cli: error: option --expiry-date is not valid for entry type 'website'
                    storepass-cli: error: option --hostname is not valid for entry type 'website'
                    storepass-cli: error: option --keyfile is not valid for entry type 'website'
                    storepass-cli: error: option --location is not valid for entry type 'website'
                    storepass-cli: error: option --phone-number is not valid for entry type 'website'
                    storepass-cli: error: option --pin is not valid for entry type 'website'
                    storepass-cli: error: option --port is not valid for entry type 'website'
                    """))

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
                util.dedent("""\
                    storepass-cli: error: Entry 'E1 name' (element #1 in 'E1 name') does not exist
                    """))

    def test_add_present(self):
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
                util.dedent("""\
                    storepass-cli: error: Entry 'E1 name' already exists
                    """))

    def test_delete(self):
        """Check that an entry can be deleted from a database."""
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
        """Check that nested entries can be deleted from a database."""
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
                util.dedent("""\
                    storepass-cli: error: Entry 'E1 name' (element #1 in 'E1 name/E2 name') does not exist
                    """))

    def test_delete_non_empty(self):
        """Check rejection to delete a non-empty folder."""
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
        """Check that a single entry is listed correctly."""
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

    def test_list_folder(self):
        """Check that a folder entry is listed correctly."""
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

    def test_list_credit_card(self):
        """Check that a credit-card entry is listed correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent("""\
                    - E1 name: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_crypto_key(self):
        """Check that a crypto-key entry is listed correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_database(self):
        """Check that a database entry is listed correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_door(self):
        """Check that a door entry is listed correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent("""\
                    - E1 name: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_email(self):
        """Check that an email entry is listed correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_ftp(self):
        """Check that an FTP entry is listed correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_generic(self):
        """Check that a generic entry is listed correctly."""
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

    def test_list_phone(self):
        """Check that a phone entry is listed correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent("""\
                    - E1 name: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_shell(self):
        """Check that a shell entry is listed correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_remote_desktop(self):
        """Check that a remote-desktop entry is listed correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_vnc(self):
        """Check that a VNC entry is listed correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent("""\
                    - E1 name [E1 hostname]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_website(self):
        """Check that a website entry is listed correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent("""\
                    - E1 name [E1 URL]: E1 description
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_list_nested(self):
        """Check that nested entries are listed correctly."""
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
        """Check that details of a single entry are displayed correctly."""
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
                    + E1 name (generic account)
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_timezone(self):
        """Check that a date of the last change uses a configured timezone."""
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
                    |+ E1 name (generic account)
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
                    |+ E1 name (generic account)
                    |  - Last modified: Tue Jan  1 01:00:00 2019 GMT
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_folder(self):
        """Check that details of a folder entry are shown correctly."""
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

    def test_show_credit_card(self):
        """Check that details of a credit-card entry are shown correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent2("""\
                    |+ E1 name (credit card)
                    |  - Card type: E1 card type
                    |  - Card number: E1 card number
                    |  - Expiry date: E1 expiry date
                    |  - CCV: E1 CCV
                    |  - PIN: E1 PIN
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_crypto_key(self):
        """Check that details of a crypto-key entry are shown correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent2("""\
                    |+ E1 name (crypto key)
                    |  - Hostname: E1 hostname
                    |  - Certificate: E1 certificate
                    |  - Keyfile: E1 keyfile
                    |  - Password: E1 password
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_database(self):
        """Check that details of a database entry are shown correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent2("""\
                    |+ E1 name (database)
                    |  - Hostname: E1 hostname
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Database: E1 database
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_door(self):
        """Check that details of a door entry are shown correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent2("""\
                    |+ E1 name (door)
                    |  - Location: E1 location
                    |  - Code: E1 code
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_email(self):
        """Check that details of an email entry are shown correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent2("""\
                    |+ E1 name (email)
                    |  - Email: E1 email
                    |  - Hostname: E1 hostname
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_ftp(self):
        """Check that details of an FTP entry are shown correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent2("""\
                    |+ E1 name (FTP)
                    |  - Hostname: E1 hostname
                    |  - Port: E1 port
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_generic(self):
        """Check that details of a generic entry are shown correctly."""
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
                    |+ E1 name (generic account)
                    |  - Hostname: E1 hostname
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_phone(self):
        """Check that details of a phone entry are shown correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent2("""\
                    |+ E1 name (phone)
                    |  - Phone number: E1 phone number
                    |  - PIN: E1 PIN
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_shell(self):
        """Check that details of a shell entry are shown correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent2("""\
                    |+ E1 name (shell)
                    |  - Hostname: E1 hostname
                    |  - Domain: E1 domain
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_remote_desktop(self):
        """Check that details of a remote-desktop entry are shown correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent2("""\
                    |+ E1 name (remote desktop)
                    |  - Hostname: E1 hostname
                    |  - Port: E1 port
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_vnc(self):
        """Check that details of a VNC entry are shown correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent2("""\
                    |+ E1 name (VNC)
                    |  - Hostname: E1 hostname
                    |  - Port: E1 port
                    |  - Username: E1 username
                    |  - Password: E1 password
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_website(self):
        """Check that details of a website entry are shown correctly."""
        # Create a test database.
        util.write_password_db(
            self.dbname, DEFAULT_PASSWORD,
            util.dedent('''\
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
                util.dedent2("""\
                    |+ E1 name (website)
                    |  - URL: E1 URL
                    |  - Username: E1 username
                    |  - Email: E1 email
                    |  - Password: E1 password
                    |  - Description: E1 description
                    |  - Last modified: Tue Jan  1 00:00:00 2019 GMT
                    |  - Notes: E1 notes
                    """))
            self.assertEqual(cli_mock.stderr.getvalue(), "")

    def test_show_nested(self):
        """Check that nested entries are displayed correctly."""
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
                    + E3 name (generic account)
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
