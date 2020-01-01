# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

PYTHON_FILES = storepass-cli.py storepass test setup.py

.PHONY: error
error:
	@echo "Please choose one of the following targets:" \
	    "check, coverage, dist, format, lint"
	@exit 1

UNITTEST_ARGS = -m unittest discover \
                 --top-level-directory . --start-directory test

.PHONY: check
check:
	python3 $(UNITTEST_ARGS)

.PHONY: coverage
coverage:
	coverage3 run --source storepass,test $(UNITTEST_ARGS)
	coverage3 html
	xdg-open htmlcov/index.html

.PHONY: dist
dist:
	python3 setup.py sdist

.PHONY: format
format:
	yapf --style=yapfrc --in-place --recursive $(PYTHON_FILES)

.PHONY: lint
lint:
	pylint --rcfile=pylintrc $(PYTHON_FILES)
