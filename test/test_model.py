# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Tests for the model module."""

import storepass.model
from . import util


class TestModel(util.StorePassTestCase):
    """Tests for the model module."""
    def test_path_string_to_spec(self):
        """Check the behaviour of path_string_to_spec()."""
        self.assertEqual(storepass.model.path_string_to_spec(""), [""])
        self.assertEqual(storepass.model.path_string_to_spec("a"), ["a"])
        self.assertEqual(storepass.model.path_string_to_spec("a/"), ["a", ""])
        self.assertEqual(storepass.model.path_string_to_spec("a/b"),
                         ["a", "b"])
        self.assertEqual(storepass.model.path_string_to_spec("a\\/b"), ["a/b"])
        self.assertEqual(storepass.model.path_string_to_spec("a\\\\b"),
                         ["a\\b"])

        with self.assertRaises(storepass.exc.ModelException) as cm:
            storepass.model.path_string_to_spec("a\\")
        self.assertEqual(
            str(cm.exception),
            "Entry name 'a\\' has an incomplete escape sequence at its end")

        with self.assertRaises(storepass.exc.ModelException) as cm:
            storepass.model.path_string_to_spec("a\\b")
        self.assertEqual(
            str(cm.exception),
            "Entry name 'a\\b' contains invalid escape sequence '\\b'")

    def test_path_spec_to_string(self):
        """Check the behaviour of path_spec_to_string()."""
        self.assertEqual(storepass.model.path_spec_to_string([""]), "")
        self.assertEqual(storepass.model.path_spec_to_string(["a"]), "a")
        self.assertEqual(storepass.model.path_spec_to_string(["a", ""]), "a/")
        self.assertEqual(storepass.model.path_spec_to_string(["a", "b"]),
                         "a/b")
        self.assertEqual(storepass.model.path_spec_to_string(["a/b"]), "a\\/b")
        self.assertEqual(storepass.model.path_spec_to_string(["a\\b"]),
                         "a\\\\b")
