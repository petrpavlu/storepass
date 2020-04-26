# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import enum
import gi
import importlib.resources
import os
import sys

gi.require_version('Gdk', '3.0')
from gi.repository import Gdk

gi.require_version('Gtk', '3.0')
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gtk

import storepass.exc
import storepass.model
import storepass.storage
from storepass.gtk import edit
from storepass.gtk import util


# Note: Keep these constants in sync with the ui files.
class _EntriesTreeStoreColumn(enum.IntEnum):
    NAME = 0
    ENTRY = 1


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources',
                                  'password_dialog.ui'))
class _PasswordDialog(Gtk.Dialog):
    """Dialog to prompt the user for a database password."""

    __gtype_name__ = "PasswordDialog"

    _password_entry = Gtk.Template.Child('password_entry')

    def __init__(self, parent_window):
        super().__init__(parent=parent_window)

    def get_password(self):
        return self._password_entry.get_text()


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources',
                                  'about_dialog.ui'))
class _AboutDialog(Gtk.AboutDialog):
    """About application dialog."""

    __gtype_name__ = "AboutDialog"


class _EntryGObject(GObject.Object):
    """Wrapper of storepass.model.Entry in GObject.Object."""
    def __init__(self, entry):
        super().__init__()
        self.entry = entry


class TreeStorePopulator(storepass.model.ModelVisitor):
    def __init__(self, tree_store):
        super().__init__()

        self._tree_store = tree_store

    def visit_root(self, root):
        return self._tree_store.append(
            None,
            ["Password Database", _EntryGObject(root)])

    def visit_folder(self, folder):
        parent_iter = self.get_path_data(folder.parent)
        return self._tree_store.append(
            parent_iter, [folder.name, _EntryGObject(folder)])

    def visit_generic(self, generic):
        parent_iter = self.get_path_data(generic.parent)
        return self._tree_store.append(
            parent_iter, [generic.name, _EntryGObject(generic)])


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources', 'main_window.ui'))
class _MainWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    _entries_tree_view = Gtk.Template.Child('entries_tree_view')
    _entries_tree_view_column = Gtk.Template.Child('entries_tree_view_column')
    _entries_tree_view_icon_renderer = Gtk.Template.Child(
        'entries_tree_view_icon_renderer')
    _db_filename_box = Gtk.Template.Child('db_filename_box')
    _db_filename_label = Gtk.Template.Child('db_filename_label')
    _entry_name_box = Gtk.Template.Child('entry_name_box')
    _entry_name_label = Gtk.Template.Child('entry_name_label')
    _entry_description_box = Gtk.Template.Child('entry_description_box')
    _entry_description_label = Gtk.Template.Child('entry_description_label')
    _entry_updated_box = Gtk.Template.Child('entry_updated_box')
    _entry_updated_label = Gtk.Template.Child('entry_updated_label')
    _entry_notes_box = Gtk.Template.Child('entry_notes_box')
    _entry_notes_label = Gtk.Template.Child('entry_notes_label')
    _entry_generic_hostname_box = Gtk.Template.Child(
        'entry_generic_hostname_box')
    _entry_generic_hostname_label = Gtk.Template.Child(
        'entry_generic_hostname_label')
    _entry_generic_username_box = Gtk.Template.Child(
        'entry_generic_username_box')
    _entry_generic_username_label = Gtk.Template.Child(
        'entry_generic_username_label')
    _entry_generic_password_box = Gtk.Template.Child(
        'entry_generic_password_box')
    _entry_generic_password_label = Gtk.Template.Child(
        'entry_generic_password_label')

    def __init__(self, application):
        super().__init__(application=application)

        # Connect main menu actions.
        new_action = Gio.SimpleAction.new('new', None)
        new_action.connect('activate', self._on_new)
        self.add_action(new_action)

        open_action = Gio.SimpleAction.new('open', None)
        open_action.connect('activate', self._on_open)
        self.add_action(open_action)

        save_action = Gio.SimpleAction.new('save', None)
        save_action.connect('activate', self._on_save)
        self.add_action(save_action)

        save_as_action = Gio.SimpleAction.new('save_as', None)
        save_as_action.connect('activate', self._on_save_as)
        self.add_action(save_as_action)

        # Initialize the entries tree view.
        tree_store = Gtk.TreeStore(str, _EntryGObject)
        tree_store.set_sort_column_id(_EntriesTreeStoreColumn.NAME,
                                      Gtk.SortType.ASCENDING)
        self._entries_tree_view.set_model(tree_store)
        self._entries_tree_view_column.set_cell_data_func(
            self._entries_tree_view_icon_renderer, self._map_entry_icon)

        menu_xml = importlib.resources.read_text('storepass.gtk.resources',
                                                 'entries_tree_view_menu.ui')
        builder = Gtk.Builder.new_from_string(menu_xml, -1)
        self._entries_tree_view_menu = Gtk.Menu.new_from_model(
            builder.get_object('entries_tree_view_menu'))
        self._entries_tree_view_menu.attach_to_widget(self._entries_tree_view)
        self._entries_tree_view_menu_row_ref = None
        self._entries_tree_view_menu.connect(
            'selection-done', self._on_entries_tree_view_menu_selection_done)

        edit_entry_action = Gio.SimpleAction.new('edit_entry', None)
        edit_entry_action.connect('activate', self._on_edit_entry)
        self.add_action(edit_entry_action)

        remove_entry_action = Gio.SimpleAction.new('remove_entry', None)
        remove_entry_action.connect('activate', self._on_remove_entry)
        self.add_action(remove_entry_action)

        add_folder_action = Gio.SimpleAction.new('add_folder', None)
        add_folder_action.connect('activate', self._on_add_folder)
        self.add_action(add_folder_action)

        add_account_action = Gio.SimpleAction.new('add_account', None)
        add_account_action.connect('activate', self._on_add_account)
        self.add_action(add_account_action)

        # Create an empty database storage and model.
        self._storage = None
        self._model = storepass.model.Model()

    def run_default_actions(self):
        """
        Run the default actions when the main window gets constructed and
        displayed.
        """

        # Try to open the default password database.
        default_database = os.path.join(os.path.expanduser('~'),
                                        '.storepass.db')
        if os.path.exists(default_database):
            self._open_password_database(default_database)

    def _clear_state(self):
        """Clear the current state. The result is a blank database."""

        self._storage = None
        self._model = storepass.model.Model()
        self._populate_tree_view()

    def _map_entry_icon(self, tree_column, cell, tree_model, iter_, data):
        """
        Set an icon name for each item in the entries tree view based on its
        type. This is a Gtk.TreeCellDataFunc callback.
        """

        assert tree_column == self._entries_tree_view_column
        assert cell == self._entries_tree_view_icon_renderer
        assert tree_model == self._entries_tree_view.get_model()

        entry = tree_model.get_value(iter_,
                                     _EntriesTreeStoreColumn.ENTRY).entry
        if isinstance(entry, storepass.model.Root):
            cell.props.icon_name = 'x-office-address-book'
        elif isinstance(entry, storepass.model.Folder):
            cell.props.icon_name = 'folder'
        else:
            cell.props.icon_name = 'x-office-document'

    def _on_new(self, action, param):
        """
        Handle the New action which is used to start a new (empty) password
        database.
        """

        self._clear_state()

    def _on_open(self, action, param):
        """
        Handle the Open action which is used to open an already existing
        password database.

        The complete operation consists of the following steps:
        1) Display a file dialog to select a password database file:
           _on_open() -> _on_open_dialog_response().
        2) Display a dialog to prompt the password for the database:
           _open_password_database() ->
           _on_open_password_database_dialog_response().
        3) Complete opening the database:
           _open_password_database2().
        """

        # Display a dialog to select a database file to open.
        dialog = Gtk.FileChooserDialog(
            "Open File",
            self,
            Gtk.FileChooserAction.OPEN,
            ("_Cancel", Gtk.ResponseType.CANCEL, "_Ok", Gtk.ResponseType.OK),
            modal=True)
        dialog.connect('response', self._on_open_dialog_response)
        dialog.show()

    def _on_open_dialog_response(self, dialog, response_id):
        """Process a response from the Open File dialog."""

        assert isinstance(dialog, Gtk.FileChooserDialog)

        if response_id != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        filename = dialog.get_filename()
        dialog.destroy()

        # Continue the process of opening the file.
        self._open_password_database(filename)

    def _open_password_database(self, filename):
        """Open a password database specified by the filename."""

        self._clear_state()

        # Ask for the password via a dialog.
        dialog = _PasswordDialog(self)
        dialog.connect('response',
                       self._on_open_password_database_dialog_response,
                       filename)
        dialog.show()
        dialog.present_with_time(Gdk.CURRENT_TIME)

    def _on_open_password_database_dialog_response(self, dialog, response_id,
                                                   filename):
        """Process a response from a Password dialog (for database open)."""

        assert isinstance(dialog, _PasswordDialog)

        if response_id != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        password = dialog.get_password()
        dialog.destroy()

        # Finalize opening the database.
        self._open_password_database2(filename, password)

    def _open_password_database2(self, filename, password):
        """
        Complete the process of opening a password database by actually loading
        it into the program.
        """

        storage = storepass.storage.Storage(filename, password)
        model = storepass.model.Model()
        try:
            model.load(storage)
        except storepass.exc.StorageReadException as e:
            # Show a dialog with the error.
            util.show_error_dialog(
                self, "Error loading password database",
                f"Failed to load password database '{filename}': {e}.")
            return

        self._storage = storage
        self._model = model
        self._populate_tree_view()

    def _on_save(self, action, param):
        """
        Handle the Save action which is used to store the currently opened
        password database on disk.
        """

        # Redirect to the Save As action if this is a new database and its
        # filename has not been specified yet.
        if self._storage is None:
            self._on_save_as(action, param)
            return

        self._model.save(self._storage)

    def _on_save_as(self, action, param):
        """
        Handle the Save As action which is used to store the currently opened
        password database on disk under a new name.

        The complete operation consists of the following steps:
        1) Display a file dialog to specify a new filename for the password
           database:
           _on_save_as() -> _on_save_as_dialog_response().
        2) Display a dialog to prompt the password for the database:
           _save_as_password_database() ->
           _on_save_as_password_database_dialog_response().
           If the database already has a password then this step is skipped.
        3) Complete saving the database:
           _save_as_password_database2().
        """

        # Display a dialog to specify a new filename where to store the
        # database.
        dialog = Gtk.FileChooserDialog(
            "Save As",
            self,
            Gtk.FileChooserAction.SAVE,
            ("_Cancel", Gtk.ResponseType.CANCEL, "_Ok", Gtk.ResponseType.OK),
            modal=True)
        dialog.connect('response', self._on_save_as_dialog_response)
        dialog.show()

    def _on_save_as_dialog_response(self, dialog, response_id):
        """Process a response from the Save As dialog."""

        assert isinstance(dialog, Gtk.FileChooserDialog)

        if response_id != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        filename = dialog.get_filename()
        dialog.destroy()

        # Continue the process of opening the file. If the database already has
        # a password specified then proceed to saving it, else first prompt for
        # the password.
        if self._storage is not None:
            self._save_as_password_database2(filename, self._storage.password)
        else:
            self._save_as_password_database(filename)

    def _save_as_password_database(self, filename):
        """Save a password database to the specified file."""

        # Ask for the password via a dialog.
        dialog = _PasswordDialog(self)
        dialog.connect('response',
                       self._on_save_password_database_dialog_response,
                       filename)
        dialog.show()
        dialog.present_with_time(Gdk.CURRENT_TIME)

    def _on_save_password_database_dialog_response(self, dialog, response_id,
                                                   filename):
        """Process a response from a Password dialog (for database save)."""

        assert isinstance(dialog, _PasswordDialog)

        if response_id != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        password = dialog.get_password()
        dialog.destroy()

        # Finalize saving the database.
        self._save_as_password_database2(filename, password)

    def _save_as_password_database2(self, filename, password):
        """
        Complete the process of saving a password database by actually storing
        it into a file.
        """

        self._storage = storepass.storage.Storage(filename, password)
        try:
            self._model.save(self._storage)
        except storepass.exc.StorageWriteException as e:
            util.show_error_dialog(
                self, "Error saving password database",
                f"Failed to save password database '{filename}': {e}.")

    def _populate_tree_view(self):
        tree_store = self._entries_tree_view.get_model()
        tree_store.clear()
        self._model.visit_all(TreeStorePopulator(tree_store))

        # Expand the root node.
        root_iter = tree_store.get_iter_first()
        assert root_iter is not None
        self._entries_tree_view.expand_row(tree_store.get_path(root_iter),
                                           False)

    def _update_entry_property(self, box_widget, label_widget, text,
                               hide_if_empty):
        if text is not None:
            box_widget.show()
            label_widget.set_text(text)
            label_widget.show()
        else:
            if hide_if_empty:
                box_widget.hide()
            label_widget.set_text("")
            label_widget.hide()

    @Gtk.Template.Callback('on_entries_tree_view_selection_changed')
    def _on_entries_tree_view_selection_changed(self, tree_selection):
        """
        Handle a changed selection in the entries tree view by updating the
        main information panel and displaying details of a selected entry.
        """

        tree_store, entry_iter = tree_selection.get_selected()
        entry = tree_store.get_value(
            entry_iter, _EntriesTreeStoreColumn.ENTRY
        ).entry if entry_iter is not None else None

        # Handle the root selection by displaying database properties.
        if entry is not None and isinstance(entry, storepass.model.Root):
            if self._storage is not None:
                db_filename = self._storage.filename
            else:
                db_filename = "<unsaved>"
        else:
            db_filename = None
        self._update_entry_property(self._db_filename_box,
                                    self._db_filename_label, db_filename, True)

        if entry is None or isinstance(entry, storepass.model.Root):
            self._update_entry_property(self._entry_name_box,
                                        self._entry_name_label, None, True)
            self._update_entry_property(self._entry_description_box,
                                        self._entry_description_label, None,
                                        True)
            self._update_entry_property(self._entry_updated_box,
                                        self._entry_updated_label, None, True)
            self._update_entry_property(self._entry_notes_box,
                                        self._entry_notes_label, None, True)

            self._update_entry_property(self._entry_generic_hostname_box,
                                        self._entry_generic_hostname_label,
                                        None, True)
            self._update_entry_property(self._entry_generic_username_box,
                                        self._entry_generic_username_label,
                                        None, True)
            self._update_entry_property(self._entry_generic_password_box,
                                        self._entry_generic_password_label,
                                        None, True)
            return

        # Show information for a password entry.
        assert isinstance(entry, storepass.model.Entry)

        self._update_entry_property(self._entry_name_box,
                                    self._entry_name_label, entry.name, False)
        self._update_entry_property(self._entry_description_box,
                                    self._entry_description_label,
                                    entry.description, False)
        self._update_entry_property(
            self._entry_updated_box, self._entry_updated_label,
            None if entry.updated is None else
            entry.updated.astimezone().strftime('%c %Z'), False)
        self._update_entry_property(self._entry_notes_box,
                                    self._entry_notes_label, entry.notes,
                                    False)

        hostname = entry.hostname if isinstance(
            entry, storepass.model.Generic) else None
        self._update_entry_property(self._entry_generic_hostname_box,
                                    self._entry_generic_hostname_label,
                                    hostname, True)
        username = entry.username if isinstance(
            entry, storepass.model.Generic) else None
        self._update_entry_property(self._entry_generic_username_box,
                                    self._entry_generic_username_label,
                                    username, True)
        password = entry.password if isinstance(
            entry, storepass.model.Generic) else None
        self._update_entry_property(self._entry_generic_password_box,
                                    self._entry_generic_password_label,
                                    password, True)

    @Gtk.Template.Callback('on_entries_tree_view_button_press_event')
    def _on_entries_tree_view_button_press_event(self, widget, event):
        """
        Handle a button press event inside the entries tree view by displaying
        a context menu if the right mouse button was pressed.
        """

        assert widget == self._entries_tree_view

        # Ignore events that are not a right mouse button press.
        if event.type != Gdk.EventType.BUTTON_PRESS or \
            event.button != Gdk.BUTTON_SECONDARY:
            return

        # Record the pointed-at row.
        path_info = widget.get_path_at_pos(event.x, event.y)
        if path_info is None:
            return
        self._entries_tree_view_menu_row_ref = Gtk.TreeRowReference(
            widget.get_model(), path_info[0])

        # Show the context menu.
        self._entries_tree_view_menu.popup_at_pointer(event)

    def _on_entries_tree_view_menu_selection_done(self, menu_shell):
        """
        Handle a completed selection in the entries tree view menu by resetting
        the current tree view row reference. This provides accurate tracking by
        the _entries_tree_view_menu_row_ref variable.

        Note that the selection-done signal is emitted after a menu action is
        performed and the signal is invoked even if the menu was cancelled.
        """

        assert menu_shell == self._entries_tree_view_menu

        self._entries_tree_view_menu_row_ref = None

    def _unwrap_entries_tree_row_reference(self, tree_row_ref):
        """
        Obtain a model that a specified row reference is currently monitoring,
        an iterator that the reference points to and an actual entry object. The
        row reference must be valid.
        """

        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        model = tree_row_ref.get_model()
        iter_ = model.get_iter(tree_row_ref.get_path())
        entry = model.get_value(iter_, _EntriesTreeStoreColumn.ENTRY).entry
        return model, iter_, entry

    def _get_entries_tree_view_menu_associated_entry(self, get_container):
        """
        Obtain the entry associated with the (opened) entries tree view menu. If
        get_container is True and the entry is not a Container then look up and
        return its parent.
        """

        assert self._entries_tree_view_menu_row_ref is not None
        assert self._entries_tree_view_menu_row_ref.valid()

        # Get the selected entry.
        tree_row_ref = self._entries_tree_view_menu_row_ref
        tree_store, entry_iter, entry = self._unwrap_entries_tree_row_reference(
            tree_row_ref)
        assert tree_store == self._entries_tree_view.get_model()

        # Look up the closest Container if the caller requires this type (for
        # example, because it is an add operation).
        if get_container and not isinstance(entry, storepass.model.Container):
            entry_iter = tree_store.iter_parent(entry_iter)
            assert entry_iter is not None

            tree_row_ref = Gtk.TreeRowReference(
                tree_store, tree_store.get_path(entry_iter))
            entry = tree_store.get_value(entry_iter,
                                         _EntriesTreeStoreColumn.ENTRY).entry
            assert isinstance(entry, storepass.model.Container)

        return tree_row_ref, entry

    def _replace_entry(self, tree_row_ref, new_entry):
        """Replace a previous entry in the model with a new one."""

        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        tree_store, entry_iter, old_entry = self._unwrap_entries_tree_row_reference(
            tree_row_ref)
        assert tree_store == self._entries_tree_view.get_model()

        try:
            self._model.replace_entry(old_entry, new_entry)
        except storepass.exc.ModelException as e:
            util.show_error_dialog(self, "Error updating entry", f"{e}.")
            return

        # Update the view.
        tree_store.set_row(
            entry_iter,
            [new_entry.name, _EntryGObject(new_entry)])

        # Update the main information panel if the changed entry is currently
        # selected.
        tree_selection = self._entries_tree_view.get_selection()
        _, selected_iter = tree_selection.get_selected()
        selected_path = tree_store.get_path(selected_iter)
        if selected_path == tree_row_ref.get_path():
            self._on_entries_tree_view_selection_changed(tree_selection)

    def _on_edit_entry(self, action, param):
        # Get the selected entry (do not require a Container).
        tree_row_ref, entry = \
            self._get_entries_tree_view_menu_associated_entry(False)

        if isinstance(entry, storepass.model.Root):
            dialog = edit.EditDatabaseDialog(self, self._storage.password)
            dialog.connect('response', self._on_edit_database_dialog_response)
        elif isinstance(entry, storepass.model.Folder):
            dialog = edit.EditFolderDialog(self, entry)
            dialog.connect('response', self._on_edit_folder_dialog_response,
                           tree_row_ref)
        else:
            dialog = edit.EditAccountDialog(self, entry)
            dialog.connect('response', self._on_edit_account_dialog_response,
                           tree_row_ref)
        dialog.show()

    def _on_edit_database_dialog_response(self, dialog, response_id):
        assert isinstance(dialog, edit.EditDatabaseDialog)

        if response_id != Gtk.ResponseType.APPLY:
            dialog.destroy()
            return

        # Obtain a new password and assign it to the storage.
        new_password = dialog.get_password()
        assert new_password is not None
        dialog.destroy()
        self._storage.password = new_password

    def _on_edit_folder_dialog_response(self, dialog, response_id,
                                        tree_row_ref):
        assert isinstance(dialog, edit.EditFolderDialog)
        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        if response_id != Gtk.ResponseType.APPLY:
            dialog.destroy()
            return

        # Obtain the newly defined folder and replace the old one.
        new_entry = dialog.get_entry()
        dialog.destroy()
        self._replace_entry(tree_row_ref, new_entry)

    def _on_edit_account_dialog_response(self, dialog, response_id,
                                         tree_row_ref):
        assert isinstance(dialog, edit.EditAccountDialog)
        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        if response_id != Gtk.ResponseType.APPLY:
            dialog.destroy()
            return

        # Obtain the newly defined account and replace the old one.
        new_entry = dialog.get_entry()
        dialog.destroy()
        self._replace_entry(tree_row_ref, new_entry)

    def _remove_entry(self, tree_row_ref):
        """
        Remove an entry from the model. If the entry is the Root then the
        whole database is cleared.
        """

        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        tree_store, entry_iter, entry = self._unwrap_entries_tree_row_reference(
            tree_row_ref)

        if isinstance(entry, storepass.model.Root):
            child_iter = tree_store.iter_children(entry_iter)
            while child_iter is not None:
                child_entry = tree_store.get_value(
                    child_iter, _EntriesTreeStoreColumn.ENTRY).entry
                entry.remove_child(child_entry)
                child_iter = child_iter if tree_store.remove(
                    child_iter) else None
        else:
            entry.parent.remove_child(entry)
            tree_store.remove(entry_iter)

    def _on_remove_confirmation_dialog_response(self, dialog, response_id,
                                                tree_row_ref):
        """
        Handle a response from a dialog displayed to confirm removal of an
        entry. If the user confirmed the operation the entry is removed.
        """

        if response_id == Gtk.ResponseType.OK:
            self._remove_entry(tree_row_ref)

        dialog.destroy()

    def _on_remove_entry(self, action, param):
        # Get the selected entry (do not require a Container).
        tree_row_ref, entry = \
            self._get_entries_tree_view_menu_associated_entry(False)

        # Remove the entry. However, if it is a Container that is not empty then
        # first prompt the user for a confirmation of the removal.
        if isinstance(entry, storepass.model.Root) and len(entry.children) > 0:
            util.show_confirmation_dialog(
                self, "Remove all entries",
                "Operation will remove all entries from the database.",
                "Remove", self._on_remove_confirmation_dialog_response,
                tree_row_ref)
        elif isinstance(entry, storepass.model.Folder) and \
             len(entry.children) > 0:
            util.show_confirmation_dialog(
                self, "Remove a non-empty folder",
                f"Folder '{entry.name}' is not empty.", "Remove",
                self._on_remove_confirmation_dialog_response, tree_row_ref)
        else:
            self._remove_entry(tree_row_ref)

    def _add_entry(self, tree_row_ref, new_entry):
        """Add a new entry in the model."""

        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        tree_store, parent_iter, parent = \
            self._unwrap_entries_tree_row_reference(tree_row_ref)
        assert tree_store == self._entries_tree_view.get_model()

        try:
            self._model.add_entry(parent, new_entry)
        except storepass.exc.ModelException as e:
            util.show_error_dialog(self, "Error adding entry", f"{e}.")
            return

        # Update the view.
        entry_iter = tree_store.append(
            parent_iter,
            [new_entry.name, _EntryGObject(new_entry)])

        # Select the newly added entry.
        self._entries_tree_view.expand_to_path(tree_store.get_path(entry_iter))
        tree_selection = self._entries_tree_view.get_selection()
        tree_selection.select_iter(entry_iter)

    def _on_add_folder(self, action, param):
        # Get the selected entry (lookup the closest Container).
        tree_row_ref, entry = \
            self._get_entries_tree_view_menu_associated_entry(True)

        dialog = edit.EditFolderDialog(self, None)
        dialog.connect('response', self._on_add_folder_dialog_response,
                       tree_row_ref)
        dialog.show()

    def _on_add_folder_dialog_response(self, dialog, response_id,
                                       tree_row_ref):
        assert isinstance(dialog, edit.EditFolderDialog)
        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        if response_id != Gtk.ResponseType.APPLY:
            dialog.destroy()
            return

        # Obtain the newly defined folder and add it.
        new_entry = dialog.get_entry()
        dialog.destroy()
        self._add_entry(tree_row_ref, new_entry)

    def _on_add_account(self, action, param):
        # Get the selected entry (lookup the closest Container).
        tree_row_ref, entry = \
            self._get_entries_tree_view_menu_associated_entry(True)

        dialog = edit.EditAccountDialog(self, None)
        dialog.connect('response', self._on_add_account_dialog_response,
                       tree_row_ref)
        dialog.show()

    def _on_add_account_dialog_response(self, dialog, response_id,
                                        tree_row_ref):
        assert isinstance(dialog, edit.EditAccountDialog)
        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        if response_id != Gtk.ResponseType.APPLY:
            dialog.destroy()
            return

        # Obtain the newly defined account and add it.
        new_entry = dialog.get_entry()
        dialog.destroy()
        self._add_entry(tree_row_ref, new_entry)


class _App(Gtk.Application):
    def do_startup(self):
        """Set up the application when it first starts."""

        Gtk.Application.do_startup(self)
        GLib.set_prgname("StorePass")

        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self._on_quit)
        self.add_action(quit_action)

        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self._on_about)
        self.add_action(about_action)

        menu_xml = importlib.resources.read_text('storepass.gtk.resources',
                                                 'main_menu.ui')
        builder = Gtk.Builder.new_from_string(menu_xml, -1)
        self.set_menubar(builder.get_object('main_menu'))

    def do_activate(self):
        """
        Handle a launch of the application by the desktop environment. Show its
        default first window.
        """

        window = _MainWindow(self)
        window.show()
        window.run_default_actions()

    def _on_quit(self, action, param):
        """Handle the quit action by exiting the application."""

        self.quit()

    def _on_about(self, action, param):
        """Handle the about action by showing the about application dialog."""

        dialog = _AboutDialog()
        dialog.connect('response',
                       lambda dialog, response_id: dialog.destroy())
        dialog.show()


def main():
    app = _App()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
