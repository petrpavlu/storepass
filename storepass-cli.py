#!/usr/bin/env python3

# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Local launcher for the StorePass command line interface."""

import sys
import storepass.cli.__main__

sys.exit(storepass.cli.__main__.main())
