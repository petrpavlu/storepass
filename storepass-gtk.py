#!/usr/bin/env python3

# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Local launcher for the StorePass GTK interface."""

import sys
import storepass.gtk.__main__

sys.exit(storepass.gtk.__main__.main())
