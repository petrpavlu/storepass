# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

PYTHON_FILES = storepass-cli.py storepass-gtk.py storepass tests setup.py

.PHONY: error
error:
	@echo "Please choose one of the following targets:" \
	    "check, codestyle, coverage, dist, docstyle, format, lint"
	@exit 1

UNITTEST_ARGS = -m unittest discover \
                 --top-level-directory . --start-directory tests

.PHONY: check
check:
	python3 $(UNITTEST_ARGS)

.PHONY: codestyle
codestyle:
	pycodestyle $(PYTHON_FILES)

.PHONY: coverage
coverage:
	coverage3 run --source storepass,tests $(UNITTEST_ARGS)
	coverage3 html
	xdg-open htmlcov/index.html

.PHONY: dist
dist:
	python3 setup.py sdist

.PHONY: docstyle
docstyle:
	pydocstyle $(PYTHON_FILES)

.PHONY: format
format:
	yapf --in-place --recursive --verbose $(PYTHON_FILES)

.PHONY: lint
lint:
	pylint $(PYTHON_FILES)
