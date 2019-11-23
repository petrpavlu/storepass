# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import storepass.cli.__main__
from . import helpers

import contextlib
import io
import unittest.mock

DEFAULT_PASSWORD = 'qwerty'

class CLIMock:
    def __init__(self, getpass, stdout, stderr):
        self.getpass = getpass
        self.stdout = stdout
        self.stderr = stderr

@contextlib.contextmanager
def cli_context(args):
    with unittest.mock.patch('getpass.getpass') as getpass, \
         unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as out, \
         unittest.mock.patch('sys.stderr', new_callable=io.StringIO) as err, \
         unittest.mock.patch('sys.argv', args):
        yield CLIMock(getpass, out, err)

class TestCLI(helpers.StorePassTestCase):
    def test_help(self):
        """Check the basic --help output."""

        with cli_context(['storepass-cli', '--help']) as cli_mock:
            cli_mock.getpass.return_value = DEFAULT_PASSWORD
            res = storepass.cli.__main__.main()
            self.assertEqual(res, 0)
            cli_mock.getpass.assert_not_called()
            self.assertEqual(cli_mock.stdout.getvalue(), '''\
usage: storepass-cli [-h] [-f PASSDB] [-v]
                     {list,show,add,delete,edit,dump} ...

positional arguments:
  {list,show,add,delete,edit,dump}

optional arguments:
  -h, --help            show this help message and exit
  -f PASSDB, --file PASSDB
                        password database file (the default is
                        ~/.storepass.db)
  -v, --verbose         increase verbosity level
''')
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
            self.assertEqual(cli_mock.stderr.getvalue(), '''\
storepass-cli: error: failed to load password database \'missing.db\': [Errno 2] No such file or directory: \'missing.db\'
''')
