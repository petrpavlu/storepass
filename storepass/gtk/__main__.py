# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import datetime
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
        return None

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

        # Initialize the entries TreeView.
        self._entries_tree_store = Gtk.TreeStore(str, _EntryGObject)
        self._entries_tree_store.set_sort_column_id(
            _EntriesTreeStoreColumn.NAME, Gtk.SortType.ASCENDING)
        self._entries_tree_view.set_model(self._entries_tree_store)

        menu_xml = importlib.resources.read_text('storepass.gtk.resources',
                                                 'entries_tree_view_menu.ui')
        builder = Gtk.Builder.new_from_string(menu_xml, -1)
        self._entries_tree_view_menu = Gtk.Menu.new_from_model(
            builder.get_object('entries_tree_view_menu'))
        self._entries_tree_view_menu.attach_to_widget(self._entries_tree_view)

        edit_action = Gio.SimpleAction.new('entry_edit', None)
        edit_action.connect('activate', self._on_entry_edit)
        self.add_action(edit_action)

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

    def _show_error_dialog(self, primary_text, secondary_text):
        """Create and display an error dialog."""

        dialog = Gtk.MessageDialog(
            self, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, primary_text)
        dialog.format_secondary_text(secondary_text)
        dialog.connect('response',
                       lambda dialog, response_id: dialog.destroy())
        dialog.show()

    def _clear_state(self):
        """Clear the current state. The result is a blank database."""

        self._storage = None
        self._model = storepass.model.Model()
        self._entries_tree_store.clear()

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
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK,
             Gtk.ResponseType.OK),
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
        dialog.connect(
            'response', lambda dialog, response_id: self
            ._on_open_password_database_dialog_response(
                dialog, response_id, filename))
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

        self._storage = storepass.storage.Storage(filename, password)
        self._model = storepass.model.Model()
        try:
            self._model.load(self._storage)
        except storepass.exc.StorageReadException as e:
            # Reset back to the clear state.
            self._clear_state()

            # Show a dialog with the error.
            self._show_error_dialog(
                "Error loading password database",
                f"Failed to load password database '{filename}': {e}.")
            return

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
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK,
             Gtk.ResponseType.OK),
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
        dialog.connect(
            'response', lambda dialog, response_id: self
            ._on_save_password_database_dialog_response(
                dialog, response_id, filaname))
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
            # Show a dialog with the error.
            self._show_error_dialog(
                "Error saving password database",
                f"Failed to save password database '{filename}': {e}.")

    def _populate_tree_view(self):
        self._model.visit_all(TreeStorePopulator(self._entries_tree_store))

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

    @Gtk.Template.Callback("on_entries_tree_view_selection_changed")
    def _on_entries_tree_view_selection_changed(self, tree_selection):
        tree_model, entry_iter = tree_selection.get_selected()
        if entry_iter is None:
            self._update_entry_property(self._entry_name_box,
                                        self._entry_name_label, None, False)
            self._update_entry_property(self._entry_description_box,
                                        self._entry_description_label, None,
                                        False)
            self._update_entry_property(self._entry_updated_box,
                                        self._entry_updated_label, None, False)
            self._update_entry_property(self._entry_notes_box,
                                        self._entry_notes_label, None, False)

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

        entry = tree_model.get_value(entry_iter,
                                     _EntriesTreeStoreColumn.ENTRY).entry

        # Show the panel with details of the entry.
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

    @Gtk.Template.Callback("on_entries_tree_view_button_press_event")
    def _on_entries_tree_view_button_press_event(self, widget, event):
        assert widget == self._entries_tree_view

        if event.type == Gdk.EventType.BUTTON_PRESS and \
            event.button == Gdk.BUTTON_SECONDARY:
            self._entries_tree_view_menu.popup_at_pointer(event)

    def _on_entry_edit(self, action, param):
        tree_selection = self._entries_tree_view.get_selection()
        tree_model, entry_iter = tree_selection.get_selected()
        assert entry_iter is not None

        entry = tree_model.get_value(entry_iter,
                                     _EntriesTreeStoreColumn.ENTRY).entry
        if isinstance(entry, storepass.model.Folder):
            dialog = edit.FolderEditDialog(self, entry)
            dialog.connect(
                'response', lambda dialog,
                response_id: self._on_folder_edit_dialog_response(
                    dialog, response_id, entry, entry_iter))
        else:
            dialog = edit.AccountEditDialog(self, entry)
            dialog.connect(
                'response', lambda dialog,
                response_id: self._on_account_edit_dialog_response(
                    dialog, response_id, entry, entry_iter))
        dialog.show()

    def _replace_entry(self, tree_store_iter, old_entry, new_entry):
        """Replace a previous entry in the model with a new one."""

        try:
            self._model.replace_entry(old_entry, new_entry)
        except storepass.exc.ModelException as e:
            # Show a dialog with the error.
            self._show_error_dialog("Error updating entry", f"{e}.")
            return

        # Update the view.
        self._entries_tree_store.set_row(
            tree_store_iter,
            [new_entry.name, _EntryGObject(new_entry)])

        # TODO Update the main panel with detailed information.

    def _get_current_datetime(self):
        return datetime.datetime.now(datetime.timezone.utc)

    def _on_folder_edit_dialog_response(self, dialog, response_id, old_entry,
                                        tree_store_iter):
        assert isinstance(dialog, edit.FolderEditDialog)
        assert isinstance(old_entry, storepass.model.Folder)

        if response_id != Gtk.ResponseType.APPLY:
            dialog.destroy()
            return

        # Obtain updated properties and create a new entry.
        name = dialog.get_name()
        if name is None:
            self._show_error_dialog("Invalid folder name",
                                    "Name cannot be empty.")
            dialog.destroy()
            return
        new_entry = storepass.model.Folder(name, dialog.get_description(),
                                           self._get_current_datetime(),
                                           dialog.get_notes(), [])

        dialog.destroy()
        self._replace_entry(tree_store_iter, old_entry, new_entry)

    def _on_account_edit_dialog_response(self, dialog, response_id, old_entry,
                                         tree_store_iter):
        assert isinstance(dialog, edit.AccountEditDialog)
        assert isinstance(old_entry, storepass.model.Account)

        if response_id != Gtk.ResponseType.APPLY:
            dialog.destroy()
            return

        # Obtain updated properties and create a new entry.
        name = dialog.get_name()
        if name is None:
            self._show_error_dialog("Invalid account name",
                                    "Name cannot be empty.")
            dialog.destroy()
            return
        description = dialog.get_description()
        updated = self._get_current_datetime()
        notes = dialog.get_notes()

        account_type = dialog.get_account_type()
        if account_type == storepass.model.Generic:
            new_entry = storepass.model.Generic(name, description, updated,
                                                notes, dialog.get_hostname(),
                                                dialog.get_username(),
                                                dialog.get_password())
        else:
            assert 0 and "Unhandled entry type!"

        dialog.destroy()
        self._replace_entry(tree_store_iter, old_entry, new_entry)


class _App(Gtk.Application):
    def __init__(self):
        super().__init__()

    def do_startup(self):
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
        window = _MainWindow(self)
        window.show()
        window.run_default_actions()

    def _on_quit(self, action, param):
        self.quit()

    def _on_about(self, action, param):
        dialog = _AboutDialog()
        dialog.connect('response',
                       lambda dialog, response_id: dialog.destroy())
        dialog.show()


def main():
    app = _App()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
