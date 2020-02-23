# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import gi
import importlib.resources

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import storepass.model


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources',
                                  'folder_edit_dialog.ui'))
class _FolderEditWindow(Gtk.Dialog):
    __gtype_name__ = "FolderEditWindow"

    _name_entry = Gtk.Template.Child('name_entry')
    _description_entry = Gtk.Template.Child('description_entry')
    _notes_textview = Gtk.Template.Child('notes_textview')

    def __init__(self, parent_window, entry):
        super().__init__(parent=parent_window)
        self._entry = entry

        self._name_entry.set_text(entry.name)
        self._description_entry.set_text(
            entry.description if entry.description is not None else "")
        self._description_entry.get_buffer().set_text(
            entry.notes if entry.notes is not None else "", -1)


def edit(parent_window, entry):
    if isinstance(entry, storepass.model.Folder):
        window = _FolderEditWindow(parent_window, entry)
    else:
        # TODO Implement.
        #window = _AccountEditWindow(parent_window, entry)
        print("Editing accounts not implemented")
    window.show()
