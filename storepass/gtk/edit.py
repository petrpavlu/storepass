# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import enum
import gi
import importlib.resources

gi.require_version('Gtk', '3.0')
from gi.repository import GObject
from gi.repository import Gtk

import storepass.model


def _normalize_empty_to_none(text):
    return text if text != "" else None


def _normalize_none_to_empty(text):
    return text if text is not None else ""


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources',
                                  'folder_edit_dialog.ui'))
class FolderEditDialog(Gtk.Dialog):
    """Dialog to edit folder properties."""

    __gtype_name__ = "FolderEditDialog"

    _name_entry = Gtk.Template.Child('name_entry')
    _description_entry = Gtk.Template.Child('description_entry')
    _notes_text_view = Gtk.Template.Child('notes_text_view')

    def __init__(self, parent_window, entry):
        super().__init__(parent=parent_window)

        if entry is None:
            return

        self._name_entry.set_text(entry.name)
        self._description_entry.set_text(
            _normalize_none_to_empty(entry.description))
        self._notes_text_view.get_buffer().set_text(
            _normalize_none_to_empty(entry.notes))

    def get_name(self):
        return _normalize_empty_to_none(self._name_entry.get_text())

    def get_description(self):
        return _normalize_empty_to_none(self._description_entry.get_text())

    def get_notes(self):
        text_buffer = self._notes_text_view.get_buffer()
        text = text_buffer.get_text(text_buffer.get_start_iter(),
                                    text_buffer.get_end_iter(), True)
        return _normalize_empty_to_none(text)


class _AccountClassGObject(GObject.Object):
    """Wrapper of storepass.model.Account sub-classes in GObject.Object."""
    def __init__(self, type_):
        super().__init__()
        self.type_ = type_


class _AccountListStoreColumn(enum.IntEnum):
    NAME = 0
    ACCOUNT_CLASS = 1


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources',
                                  'account_edit_dialog.ui'))
class AccountEditDialog(Gtk.Dialog):
    """Dialog to edit account properties."""

    __gtype_name__ = "AccountEditDialog"

    _name_entry = Gtk.Template.Child('name_entry')
    _description_entry = Gtk.Template.Child('description_entry')
    _notes_text_view = Gtk.Template.Child('notes_text_view')
    _type_combo_box = Gtk.Template.Child('type_combo_box')
    _hostname_label = Gtk.Template.Child('hostname_label')
    _hostname_entry = Gtk.Template.Child('hostname_entry')
    _username_label = Gtk.Template.Child('username_label')
    _username_entry = Gtk.Template.Child('username_entry')
    _password_label = Gtk.Template.Child('password_label')
    _password_entry = Gtk.Template.Child('password_entry')

    def __init__(self, parent_window, entry):
        super().__init__(parent=parent_window)

        self._name_entry.set_text(entry.name)
        self._description_entry.set_text(
            _normalize_none_to_empty(entry.description))
        self._notes_text_view.get_buffer().set_text(
            _normalize_none_to_empty(entry.notes))

        self._type_list_store = Gtk.ListStore(str, _AccountClassGObject)
        self._type_list_store.append(
            ["Generic",
             _AccountClassGObject(storepass.model.Generic)])
        self._type_combo_box.set_model(self._type_list_store)
        self._type_combo_box.set_active(0)

        if isinstance(entry, storepass.model.Generic):
            self._hostname_entry.set_text(
                _normalize_none_to_empty(entry.hostname))
        if isinstance(entry, storepass.model.Generic):
            self._username_entry.set_text(
                _normalize_none_to_empty(entry.username))
        if isinstance(entry, storepass.model.Generic):
            self._password_entry.set_text(
                _normalize_none_to_empty(entry.password))

    @Gtk.Template.Callback("on_type_combo_box_changed")
    def _on_type_combo_box_changed(self, combo_box):
        assert combo_box == self._type_combo_box

        show_hostname = False
        show_username = False
        show_password = False

        active_iter = combo_box.get_active_iter()
        assert active_iter is not None
        account_class = combo_box.get_model().get_value(
            active_iter, _AccountListStoreColumn.ACCOUNT_CLASS)
        if account_class.type_ == storepass.model.Generic:
            show_hostname = True
            show_username = True
            show_password = True
        else:
            assert 0 and "Unhandled entry type!"

        self._hostname_label.set_visible(show_hostname)
        self._hostname_entry.set_visible(show_hostname)
        self._username_label.set_visible(show_username)
        self._username_entry.set_visible(show_username)
        self._password_label.set_visible(show_password)
        self._password_entry.set_visible(show_password)

    def get_name(self):
        return _normalize_empty_to_none(self._name_entry.get_text())

    def get_description(self):
        return _normalize_empty_to_none(self._description_entry.get_text())

    def get_notes(self):
        text_buffer = self._notes_text_view.get_buffer()
        text = text_buffer.get_text(text_buffer.get_start_iter(),
                                    text_buffer.get_end_iter(), True)
        return _normalize_empty_to_none(text)

    def get_account_type(self):
        active_iter = self._type_combo_box.get_active_iter()
        assert active_iter is not None
        account_class = self._type_combo_box.get_model().get_value(
            active_iter, _AccountListStoreColumn.ACCOUNT_CLASS)
        return account_class.type_

    def get_hostname(self):
        return _normalize_empty_to_none(self._hostname_entry.get_text())

    def get_username(self):
        return _normalize_empty_to_none(self._username_entry.get_text())

    def get_password(self):
        return _normalize_empty_to_none(self._password_entry.get_text())
