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

    def test_add_entry(self):
        """Check Model.add_entry() adds new entries correctly."""
        root = storepass.model.Root([])
        model = storepass.model.Model(root)

        # Add a folder under the root.
        folder = storepass.model.Folder("E1 name", None, None, None, [])
        model.add_entry(folder, root)
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], folder)
        self.assertEqual(len(folder.children), 0)

        # Add a generic account in the new folder.
        generic = storepass.model.Generic("E2 name", None, None, None, None,
                                          None, None)
        model.add_entry(generic, folder)
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], folder)
        self.assertEqual(len(folder.children), 1)
        self.assertEqual(folder.children[0], generic)

    def test_add_entry_duplicated(self):
        """Check Model.add_entry() rejects adding a duplicated entry."""
        folder = storepass.model.Folder("E1 name", None, None, None, [])
        root = storepass.model.Root([folder])
        model = storepass.model.Model(root)

        # Add the first entry.
        generic_0 = storepass.model.Generic("E2 name", None, None, None, None,
                                            None, None)
        model.add_entry(generic_0, folder)

        # Try adding the second entry.
        generic_1 = storepass.model.Generic("E2 name", None, None, None, None,
                                            None, None)
        with self.assertRaises(storepass.exc.ModelException) as cm:
            model.add_entry(generic_1, folder)
        self.assertEqual(str(cm.exception),
                         "Entry 'E1 name/E2 name' already exists")
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], folder)
        self.assertEqual(len(folder.children), 1)
        self.assertEqual(folder.children[0], generic_0)

    def test_move_entry(self):
        """Check Model.move_entry() moves entries correctly."""
        generic = storepass.model.Generic("E1 name", None, None, None, None,
                                          None, None)
        folder = storepass.model.Folder("E2 name", None, None, None, [generic])
        root = storepass.model.Root([folder])
        model = storepass.model.Model(root)

        # Move the generic account from the folder to the root.
        model.move_entry(generic, root)
        self.assertEqual(len(root.children), 2)
        self.assertEqual(root.children[0], generic)
        self.assertEqual(root.children[1], folder)
        self.assertEqual(len(folder.children), 0)

        # Move the generic account from the root back to the folder.
        model.move_entry(generic, folder)
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], folder)
        self.assertEqual(len(folder.children), 1)
        self.assertEqual(folder.children[0], generic)

    def test_move_entry_duplicated(self):
        """Check Model.move_entry() rejects moving on an existing entry."""
        generic_0 = storepass.model.Generic("E1 name", None, None, None, None,
                                            None, None)
        folder_0 = storepass.model.Folder("E2 name", None, None, None,
                                          [generic_0])
        generic_1 = storepass.model.Generic("E1 name", None, None, None, None,
                                            None, None)
        folder_1 = storepass.model.Folder("E3 name", None, None, None,
                                          [generic_1])
        root = storepass.model.Root([folder_0, folder_1])
        model = storepass.model.Model(root)

        # Try moving the second generic account to the first folder where an
        # entry with the same name already exists.
        with self.assertRaises(storepass.exc.ModelException) as cm:
            model.move_entry(generic_1, folder_0)
        self.assertEqual(str(cm.exception),
                         "Entry 'E2 name/E1 name' already exists")
        self.assertEqual(len(root.children), 2)
        self.assertEqual(root.children[0], folder_0)
        self.assertEqual(root.children[1], folder_1)
        self.assertEqual(len(folder_0.children), 1)
        self.assertEqual(folder_0.children[0], generic_0)
        self.assertEqual(len(folder_1.children), 1)
        self.assertEqual(folder_1.children[0], generic_1)

    def test_move_entry_under(self):
        """Check Model.move_entry() rejects moving an entry on itself."""
        folder_0 = storepass.model.Folder("E1 name", None, None, None, [])
        folder_1 = storepass.model.Folder("E2 name", None, None, None,
                                          [folder_0])
        root = storepass.model.Root([folder_1])
        model = storepass.model.Model(root)

        # Try moving the outer folder on itself.
        with self.assertRaises(storepass.exc.ModelException) as cm:
            model.move_entry(folder_1, folder_1)
        self.assertEqual(
            str(cm.exception),
            "Entry 'E2 name' cannot be moved under 'E2 name' because it "
            "constitutes a path to the latter")

        # Try moving the outer folder under the inner one.
        with self.assertRaises(storepass.exc.ModelException) as cm:
            model.move_entry(folder_1, folder_0)
        self.assertEqual(
            str(cm.exception),
            "Entry 'E2 name' cannot be moved under 'E2 name/E1 name' because "
            "it constitutes a path to the latter")
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], folder_1)
        self.assertEqual(len(folder_1.children), 1)
        self.assertEqual(folder_1.children[0], folder_0)
        self.assertEqual(len(folder_0.children), 0)

    def test_remove_entry(self):
        """Check Model.remove_entry() removes entries correctly."""
        generic = storepass.model.Generic("E1 name", None, None, None, None,
                                          None, None)
        folder = storepass.model.Folder("E2 name", None, None, None, [generic])
        root = storepass.model.Root([folder])
        model = storepass.model.Model(root)

        # Remove the generic account.
        model.remove_entry(generic)
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], folder)
        self.assertEqual(len(folder.children), 0)

        # Remove the folder.
        model.remove_entry(folder)
        self.assertEqual(len(root.children), 0)

    def test_remove_entry_non_empty(self):
        """Check Model.remove_entry() rejects removing a non-empty folder."""
        generic = storepass.model.Generic("E1 name", None, None, None, None,
                                          None, None)
        folder = storepass.model.Folder("E2 name", None, None, None, [generic])
        root = storepass.model.Root([folder])
        model = storepass.model.Model(root)

        # Try removing the folder.
        with self.assertRaises(storepass.exc.ModelException) as cm:
            model.remove_entry(folder)
        self.assertEqual(str(cm.exception),
                         "Entry 'E2 name' is non-empty and cannot be removed")
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], folder)
        self.assertEqual(len(folder.children), 1)
        self.assertEqual(folder.children[0], generic)

    def test_replace_entry(self):
        """Check Model.replace_entry() replaces entries correctly."""
        generic_0 = storepass.model.Generic("E1 name", None, None, None, None,
                                            None, None)
        folder = storepass.model.Folder("E2 name", None, None, None,
                                        [generic_0])
        root = storepass.model.Root([folder])
        model = storepass.model.Model(root)

        # Replace the generic account.
        generic_1 = storepass.model.Generic("E3 name", None, None, None, None,
                                            None, None)
        model.replace_entry(generic_0, generic_1)
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], folder)
        self.assertEqual(len(folder.children), 1)
        self.assertEqual(folder.children[0], generic_1)

    def test_replace_entry_duplicated(self):
        """Check Model.replace_entry() rejects rename to a duplicated entry."""
        generic_0 = storepass.model.Generic("E1 name", None, None, None, None,
                                            None, None)
        generic_1 = storepass.model.Generic("E2 name", None, None, None, None,
                                            None, None)
        folder = storepass.model.Folder("E3 name", None, None, None,
                                        [generic_0, generic_1])
        root = storepass.model.Root([folder])
        model = storepass.model.Model(root)

        # Try replacing the first generic account with an entry that has the
        # same name as the second one.
        generic_2 = storepass.model.Generic("E2 name", None, None, None, None,
                                            None, None)
        with self.assertRaises(storepass.exc.ModelException) as cm:
            model.replace_entry(generic_0, generic_2)
        self.assertEqual(str(cm.exception),
                         "Entry 'E3 name/E2 name' already exists")
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], folder)
        self.assertEqual(len(folder.children), 2)
        self.assertEqual(folder.children[0], generic_0)
        self.assertEqual(folder.children[1], generic_1)

    def test_replace_entry_empty_folder(self):
        """Check Model.replace_entry() can freely replace an empty folder."""
        folder = storepass.model.Folder("E1 name", None, None, None, [])
        root = storepass.model.Root([folder])
        model = storepass.model.Model(root)

        # Replace the (empty) folder with a generic account.
        generic = storepass.model.Generic("E2 name", None, None, None, None,
                                          None, None)
        model.replace_entry(folder, generic)
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], generic)

    def test_replace_entry_non_empty_folder(self):
        """Check Model.replace_entry() rejects losing children of a folder."""
        generic_0 = storepass.model.Generic("E1 name", None, None, None, None,
                                            None, None)
        folder = storepass.model.Folder("E2 name", None, None, None,
                                        [generic_0])
        root = storepass.model.Root([folder])
        model = storepass.model.Model(root)

        # Try replacing the (non-empty) folder with a generic account.
        generic_1 = storepass.model.Generic("E3 name", None, None, None, None,
                                            None, None)
        with self.assertRaises(storepass.exc.ModelException) as cm:
            model.replace_entry(folder, generic_1)
        self.assertEqual(
            str(cm.exception),
            "Entry 'E2 name' is non-empty and cannot be replaced by "
            "a non-folder type")
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], folder)
        self.assertEqual(len(folder.children), 1)
        self.assertEqual(folder.children[0], generic_0)

    def test_replace_entry_transfer_children(self):
        """Check Model.replace_entry() transfers children between folders."""
        generic = storepass.model.Generic("E1 name", None, None, None, None,
                                          None, None)
        folder_0 = storepass.model.Folder("E2 name", None, None, None,
                                          [generic])
        root = storepass.model.Root([folder_0])
        model = storepass.model.Model(root)

        # Replace the folder with another folder.
        folder_1 = storepass.model.Folder("E3 name", None, None, None, [])
        model.replace_entry(folder_0, folder_1)
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], folder_1)
        self.assertEqual(len(folder_1.children), 1)
        self.assertEqual(folder_1.children[0], generic)
