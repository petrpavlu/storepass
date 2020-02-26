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
class FolderEditDialog(Gtk.Dialog):
    __gtype_name__ = "FolderEditDialog"

    _name_entry = Gtk.Template.Child('name_entry')
    _description_entry = Gtk.Template.Child('description_entry')
    _notes_textview = Gtk.Template.Child('notes_textview')

    def __init__(self, parent_window, entry):
        super().__init__(parent=parent_window)

        self._name_entry.set_text(entry.name)
        self._description_entry.set_text(
            entry.description if entry.description is not None else "")
        self._notes_textview.get_buffer().set_text(
            entry.notes if entry.notes is not None else "", -1)

    def get_name(self):
        return self._name_entry.get_text()

    def get_description(self):
        text = self._description_entry.get_text()
        return text if text != "" else None

    def get_notes(self):
        text_buffer = self._notes_textview.get_buffer()
        text = text_buffer.get_text(text_buffer.get_start_iter(),
                                    text_buffer.get_end_iter(), True)
        return text if text != "" else None
