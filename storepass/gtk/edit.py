# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import datetime
import enum
import importlib.resources

import gi
gi.require_version('Gtk', '3.0')  # pylint: disable=wrong-import-position
from gi.repository import GObject
from gi.repository import Gtk

import storepass.model
from storepass.gtk import util


def _normalize_empty_to_none(text):
    return text if text != "" else None


def _normalize_none_to_empty(text):
    return text if text is not None else ""


def _get_current_datetime():
    """Obtain the current date+time in the UTC timezone."""

    return datetime.datetime.now(datetime.timezone.utc)


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources',
                                  'edit_database_dialog.ui'))
class EditDatabaseDialog(Gtk.Dialog):
    """Dialog to edit database properties."""

    __gtype_name__ = 'EditDatabaseDialog'

    _password_entry = Gtk.Template.Child('password_entry')

    def __init__(self, parent_window, password):
        super().__init__(parent=parent_window)

        # Hint correct types to pylint.
        self._password_entry = util.Hint.GtkEntry(self._password_entry)

        self.connect('response', self._on_response)

        self._password_entry.set_text(_normalize_none_to_empty(password))

    def _on_response(self, dialog, response_id):
        assert dialog == self

        if (response_id != Gtk.ResponseType.APPLY or
                self._password_entry.get_text() != ""):
            return

        # Report an error about the empty password and stop the response
        # signal.
        self.stop_emission_by_name('response')
        self._password_entry.grab_focus()
        util.show_error_dialog(self, "Invalid password",
                               "Password cannot be empty.")

    def get_password(self):
        """Return a password input by the user."""

        return self._password_entry.get_text()


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources',
                                  'edit_folder_dialog.ui'))
class EditFolderDialog(Gtk.Dialog):
    """Dialog to edit folder properties."""

    __gtype_name__ = 'EditFolderDialog'

    _modify_folder_label = Gtk.Template.Child('modify_folder_label')
    _name_entry = Gtk.Template.Child('name_entry')
    _description_entry = Gtk.Template.Child('description_entry')
    _notes_text_view = Gtk.Template.Child('notes_text_view')
    _apply_button = Gtk.Template.Child('apply_button')

    def __init__(self, parent_window, entry):
        super().__init__(parent=parent_window)

        # Hint correct types to pylint.
        self._modify_folder_label = util.Hint.GtkLabel(
            self._modify_folder_label)
        self._name_entry = util.Hint.GtkEntry(self._name_entry)
        self._description_entry = util.Hint.GtkEntry(self._description_entry)
        self._notes_text_view = util.Hint.GtkTextView(self._notes_text_view)
        self._apply_button = util.Hint.GtkButton(self._apply_button)

        self.connect('response', self._on_response)

        if entry is None:
            self.set_title("Add Folder")
            self._modify_folder_label.set_text("Add Folder")
            self._apply_button.set_label("_Add")
            return

        self.set_title("Edit Folder")
        self._modify_folder_label.set_text("Edit Folder")
        self._apply_button.set_label("_Apply")

        self._name_entry.set_text(entry.name)
        self._description_entry.set_text(
            _normalize_none_to_empty(entry.description))
        self._notes_text_view.get_buffer().set_text(
            _normalize_none_to_empty(entry.notes))

    def _on_response(self, dialog, response_id):
        assert dialog == self

        if (response_id != Gtk.ResponseType.APPLY or
                self._name_entry.get_text() != ""):
            return

        # Report an error about the empty name and stop the response signal.
        self.stop_emission_by_name('response')
        self._name_entry.grab_focus()
        util.show_error_dialog(self, "Invalid folder name",
                               "Name cannot be empty.")

    def get_entry(self):
        """Create a new folder based on the information input by the user."""

        name = _normalize_empty_to_none(self._name_entry.get_text())
        assert name is not None
        description = _normalize_empty_to_none(
            self._description_entry.get_text())
        text_buffer = self._notes_text_view.get_buffer()
        text = text_buffer.get_text(text_buffer.get_start_iter(),
                                    text_buffer.get_end_iter(), True)
        notes = _normalize_empty_to_none(text)

        return storepass.model.Folder(name, description,
                                      _get_current_datetime(), notes, [])


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
                                  'edit_account_dialog.ui'))
class EditAccountDialog(Gtk.Dialog):
    """Dialog to edit account properties."""

    __gtype_name__ = 'EditAccountDialog'

    _modify_account_label = Gtk.Template.Child('modify_account_label')
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
    _apply_button = Gtk.Template.Child('apply_button')

    def __init__(self, parent_window, entry):
        super().__init__(parent=parent_window)

        # Hint correct types to pylint.
        self._modify_account_label = util.Hint.GtkLabel(
            self._modify_account_label)
        self._name_entry = util.Hint.GtkEntry(self._name_entry)
        self._description_entry = util.Hint.GtkEntry(self._description_entry)
        self._notes_text_view = util.Hint.GtkTextView(self._notes_text_view)
        self._type_combo_box = util.Hint.GtkComboBox(self._type_combo_box)
        self._hostname_label = util.Hint.GtkLabel(self._hostname_label)
        self._hostname_entry = util.Hint.GtkEntry(self._hostname_entry)
        self._username_label = util.Hint.GtkLabel(self._username_label)
        self._username_entry = util.Hint.GtkEntry(self._username_entry)
        self._password_label = util.Hint.GtkLabel(self._password_label)
        self._password_entry = util.Hint.GtkEntry(self._password_entry)
        self._apply_button = util.Hint.GtkButton(self._apply_button)

        type_list_store = Gtk.ListStore(str, _AccountClassGObject)
        type_list_store.append(
            ["Generic",
             _AccountClassGObject(storepass.model.Generic)])
        self._type_combo_box.set_model(type_list_store)

        self.connect('response', self._on_response)

        if entry is None:
            self.set_title("Add Account")
            self._modify_account_label.set_text("Add Account")
            self._apply_button.set_label("_Add")
            self._type_combo_box.set_active(0)
            return

        self.set_title("Edit Account")
        self._modify_account_label.set_text("Edit Account")
        self._apply_button.set_label("_Apply")

        self._name_entry.set_text(entry.name)
        self._description_entry.set_text(
            _normalize_none_to_empty(entry.description))
        self._notes_text_view.get_buffer().set_text(
            _normalize_none_to_empty(entry.notes))

        # TODO Select the correct type based on entry's type.
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

    def _on_response(self, dialog, response_id):
        assert dialog == self

        if (response_id != Gtk.ResponseType.APPLY or
                self._name_entry.get_text() != ""):
            return

        # Report an error about the empty name and stop the response signal.
        self.stop_emission_by_name('response')
        self._name_entry.grab_focus()
        util.show_error_dialog(self, "Invalid account name",
                               "Name cannot be empty.")

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

    def get_entry(self):
        """Create a new account based on the information input by the user."""

        # Get common properties.
        name = _normalize_empty_to_none(self._name_entry.get_text())
        assert name is not None
        description = _normalize_empty_to_none(
            self._description_entry.get_text())
        updated = _get_current_datetime()
        text_buffer = self._notes_text_view.get_buffer()
        text = text_buffer.get_text(text_buffer.get_start_iter(),
                                    text_buffer.get_end_iter(), True)
        notes = _normalize_empty_to_none(text)

        # Get the account type.
        active_iter = self._type_combo_box.get_active_iter()
        assert active_iter is not None
        account_class = self._type_combo_box.get_model().get_value(
            active_iter, _AccountListStoreColumn.ACCOUNT_CLASS).type_

        # Create a new account.
        if account_class == storepass.model.Generic:
            hostname = _normalize_empty_to_none(
                self._hostname_entry.get_text())
            username = _normalize_empty_to_none(
                self._username_entry.get_text())
            password = _normalize_empty_to_none(
                self._password_entry.get_text())
            entry = storepass.model.Generic(name, description, updated, notes,
                                            hostname, username, password)
        else:
            assert 0 and "Unhandled entry type!"

        return entry
