# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Dialogs to edit database properties and add/edit password entries."""

import enum
import importlib.resources

import gi
gi.require_version('Gtk', '3.0')  # pylint: disable=wrong-import-position
from gi.repository import GObject
from gi.repository import Gtk

import storepass.model
import storepass.util
from storepass.gtk import util


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources',
                                  'edit_database_dialog.ui'))
class EditDatabaseDialog(Gtk.Dialog):
    """Dialog to edit database properties."""

    __gtype_name__ = 'EditDatabaseDialog'

    _password_entry = Gtk.Template.Child('password_entry')

    def __init__(self, parent_window, password):
        """Initialize a database edit dialog."""
        super().__init__(parent=parent_window)

        # Hint correct types to pylint.
        self._password_entry = util.Hint.GtkEntry(self._password_entry)

        # Initialize the dialog.
        self._password_entry.set_text(
            storepass.util.normalize_none_to_empty(password))

        self.connect('response', self._on_response)

    def _on_response(self, dialog, response_id):
        """Process a response signal from the dialog."""
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

    def __init__(self, parent_window, folder):
        """
        Initialize an add/edit folder dialog.

        Initialize a dialog to prompt the user for properties of a folder
        entry. Initial values are preset from a specified folder entry unless
        the value is None.
        """
        super().__init__(parent=parent_window)

        # Hint correct types to pylint.
        self._modify_folder_label = util.Hint.GtkLabel(
            self._modify_folder_label)
        self._name_entry = util.Hint.GtkEntry(self._name_entry)
        self._description_entry = util.Hint.GtkEntry(self._description_entry)
        self._notes_text_view = util.Hint.GtkTextView(self._notes_text_view)
        self._apply_button = util.Hint.GtkButton(self._apply_button)

        # Initialize the dialog.
        if folder is not None:
            self.set_title("Edit Folder")
            self._modify_folder_label.set_text("Edit Folder")
            self._apply_button.set_label("_Apply")

            self._name_entry.set_text(folder.name)
            self._description_entry.set_text(
                storepass.util.normalize_none_to_empty(folder.description))
            self._notes_text_view.get_buffer().set_text(
                storepass.util.normalize_none_to_empty(folder.notes))
        else:
            self.set_title("Add Folder")
            self._modify_folder_label.set_text("Add Folder")
            self._apply_button.set_label("_Add")

        self.connect('response', self._on_response)

    def _on_response(self, dialog, response_id):
        """Process a response signal from the dialog."""
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
        name = storepass.util.normalize_empty_to_none(
            self._name_entry.get_text())
        assert name is not None
        description = storepass.util.normalize_empty_to_none(
            self._description_entry.get_text())
        text_buffer = self._notes_text_view.get_buffer()
        text = text_buffer.get_text(text_buffer.get_start_iter(),
                                    text_buffer.get_end_iter(), True)
        notes = storepass.util.normalize_empty_to_none(text)

        return storepass.model.Folder(name, description,
                                      storepass.util.get_current_datetime(),
                                      notes, [])


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

    _edit_grid = Gtk.Template.Child('edit_grid')
    _modify_account_label = Gtk.Template.Child('modify_account_label')
    _name_entry = Gtk.Template.Child('name_entry')
    _description_entry = Gtk.Template.Child('description_entry')
    _notes_text_view = Gtk.Template.Child('notes_text_view')
    _type_combo_box = Gtk.Template.Child('type_combo_box')
    _account_data_label = Gtk.Template.Child('account_data_label')
    _apply_button = Gtk.Template.Child('apply_button')

    class _PropertyWidget:
        """Aggregate to record property widgets for a specific field."""
        def __init__(self, field, name_label, value_entry):
            self.field = field
            self.name_label = name_label
            self.value_entry = value_entry

    def __init__(self, parent_window, account):
        """
        Initialize an add/edit account dialog.

        Initialize a dialog to prompt the user for properties of an account
        entry. Initial values are preset from a specified account entry unless
        the value is None.
        """
        super().__init__(parent=parent_window)

        # Hint correct types to pylint.
        self._edit_grid = util.Hint.GtkGrid(self._edit_grid)
        self._modify_account_label = util.Hint.GtkLabel(
            self._modify_account_label)
        self._name_entry = util.Hint.GtkEntry(self._name_entry)
        self._description_entry = util.Hint.GtkEntry(self._description_entry)
        self._notes_text_view = util.Hint.GtkTextView(self._notes_text_view)
        self._type_combo_box = util.Hint.GtkComboBox(self._type_combo_box)
        self._account_data_label = util.Hint.GtkLabel(self._account_data_label)
        self._apply_button = util.Hint.GtkButton(self._apply_button)

        # Initialize the property value and widget recorders.
        self._properties = {}
        self._property_widgets = []

        # Initialize the account-type combo box.
        type_list_store = Gtk.ListStore(str, _AccountClassGObject)
        for entry_cls in storepass.model.ENTRY_TYPES:
            if entry_cls == storepass.model.Folder:
                continue
            type_list_store.append(
                [entry_cls.entry_label,
                 _AccountClassGObject(entry_cls)])
        self._type_combo_box.set_model(type_list_store)

        # Initialize the dialog.
        if account is not None:
            self.set_title("Edit Account")
            self._modify_account_label.set_text("Edit Account")
            self._apply_button.set_label("_Apply")

            self._name_entry.set_text(account.name)
            self._description_entry.set_text(
                storepass.util.normalize_none_to_empty(account.description))
            self._notes_text_view.get_buffer().set_text(
                storepass.util.normalize_none_to_empty(account.notes))
            self._set_properties_from_entry(account)

            self._set_selected_type(type(account))
        else:
            self.set_title("Add Account")
            self._modify_account_label.set_text("Add Account")
            self._apply_button.set_label("_Add")
            self._set_selected_type(storepass.model.Generic)

        self.connect('response', self._on_response)

    def _set_selected_type(self, new_account_cls):
        """Set a currently selected account type."""
        type_list_store = self._type_combo_box.get_model()
        iter_ = type_list_store.get_iter_first()
        index = 0
        while iter_ is not None:
            account_cls = type_list_store.get_value(
                iter_, _AccountListStoreColumn.ACCOUNT_CLASS).type_
            if account_cls == new_account_cls:
                self._type_combo_box.set_active(index)
                break

            iter_ = type_list_store.iter_next(iter_)
            index += 1
        else:
            assert 0 and "Unrecognized account type!"

    def _update_property(self, field, value):
        """Update a value of a specified property."""
        if value is not None:
            self._properties[field] = value
        elif field in self._properties:
            del self._properties[field]

    def _set_properties_from_entry(self, account):
        """Update properties from an existing entry."""
        for field in account.entry_fields:
            self._update_property(field, account.properties[field])

    def _set_properties_from_widgets(self):
        """Update properties from currently displayed property widgets."""
        for property_widget in self._property_widgets:
            value = storepass.util.normalize_empty_to_none(
                property_widget.value_entry.get_text())
            self._update_property(property_widget.field, value)

    @Gtk.Template.Callback("on_type_combo_box_changed")
    def _on_type_combo_box_changed(self, combo_box):
        """Handle a change of the selected account type."""
        assert combo_box == self._type_combo_box

        # Get the selected account type.
        active_iter = combo_box.get_active_iter()
        assert active_iter is not None
        account_cls = combo_box.get_model().get_value(
            active_iter, _AccountListStoreColumn.ACCOUNT_CLASS).type_

        # Save properties from the current property entries.
        self._set_properties_from_widgets()

        # Destroy any current property widgets.
        for property_widget in self._property_widgets:
            row = self._edit_grid.child_get_property(
                property_widget.name_label, 'top-attach')
            self._edit_grid.remove_row(row)
        self._property_widgets = []

        # Create and insert property widgets for the selected type.
        insert_at = self._edit_grid.child_get_property(
            self._account_data_label, 'top-attach') + 1

        for field in account_cls.entry_fields:
            property_xml = importlib.resources.read_text(
                'storepass.gtk.resources', 'edit_property_widgets.ui')
            builder = Gtk.Builder.new_from_string(property_xml, -1)

            self._edit_grid.insert_row(insert_at)

            name_label = builder.get_object('property_name_label')
            name_label.set_label(f"{field.label}: ")
            self._edit_grid.attach(name_label, 0, insert_at, 1, 1)

            value_entry = builder.get_object('property_value_entry')
            if field.is_protected:
                value_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
            if field in self._properties:
                value_entry.set_text(
                    storepass.util.normalize_none_to_empty(
                        self._properties[field]))
            self._edit_grid.attach(value_entry, 1, insert_at, 1, 1)

            self._property_widgets.append(
                self._PropertyWidget(field, name_label, value_entry))
            insert_at += 1

    def _on_response(self, dialog, response_id):
        """Process a response signal from the dialog."""
        assert dialog == self

        if (response_id != Gtk.ResponseType.APPLY or
                self._name_entry.get_text() != ""):
            return

        # Report an error about the empty name and stop the response signal.
        self.stop_emission_by_name('response')
        self._name_entry.grab_focus()
        util.show_error_dialog(self, "Invalid account name",
                               "Name cannot be empty.")

    def get_entry(self):
        """Create a new account based on the information input by the user."""
        # Get common properties.
        name = storepass.util.normalize_empty_to_none(
            self._name_entry.get_text())
        assert name is not None
        description = storepass.util.normalize_empty_to_none(
            self._description_entry.get_text())
        updated = storepass.util.get_current_datetime()
        text_buffer = self._notes_text_view.get_buffer()
        text = text_buffer.get_text(text_buffer.get_start_iter(),
                                    text_buffer.get_end_iter(), True)
        notes = storepass.util.normalize_empty_to_none(text)

        # Save properties from the current property entries.
        self._set_properties_from_widgets()

        # Get the selected account type.
        active_iter = self._type_combo_box.get_active_iter()
        assert active_iter is not None
        account_cls = self._type_combo_box.get_model().get_value(
            active_iter, _AccountListStoreColumn.ACCOUNT_CLASS).type_

        # Return a new account.
        return account_cls.from_proxy(name, description, updated, notes,
                                      self._properties)
