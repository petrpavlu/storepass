# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import gi
import importlib.resources
import os
import sys

gi.require_version('Gdk', '3.0')
from gi.repository import Gdk

gi.require_version('Gtk', '3.0')
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gtk

import storepass.model
import storepass.storage

# Note: Keep these constants in sync with the ui files.
ENTRIES_TREEVIEW_NAME_COLUMN = 0
ENTRIES_TREEVIEW_ENTRY_COLUMN = 1


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources',
                                  'password_dialog.ui'))
class _PasswordDialog(Gtk.Dialog):
    """Dialog to prompt the user for a database password."""

    __gtype_name__ = "PasswordDialog"

    _password_entry = Gtk.Template.Child('password_entry')

    def __init__(self, parent, filename):
        super().__init__(parent=parent)
        self._filename = filename

    def get_filename(self):
        return self._filename

    def get_password(self):
        return self._password_entry.get_text()


class _EntryGObject(GObject.Object):
    """Wrapper of storepass.model.Entry in GObject.Object."""
    def __init__(self, entry):
        super().__init__()
        self.entry = entry


class TreeStorePopulator(storepass.model.ModelVisitor):
    def __init__(self, tree_store):
        super().__init__()

        self.tree_store = tree_store

    def visit_root(self, parent, root):
        return None

    def visit_folder(self, parent, folder):
        parent_iter = self.get_path_data(parent)
        return self.tree_store.append(
            parent_iter, [folder.name, _EntryGObject(folder)])

    def visit_generic(self, parent, generic):
        parent_iter = self.get_path_data(parent)
        assert ENTRIES_TREEVIEW_NAME_COLUMN == 0
        assert ENTRIES_TREEVIEW_ENTRY_COLUMN == 1
        return self.tree_store.append(
            parent_iter, [generic.name, _EntryGObject(generic)])


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources', 'main_window.ui'))
class _MainWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    _entries_treeview = Gtk.Template.Child('entries_treeview')
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

        self._entries_treestore = Gtk.TreeStore(str, _EntryGObject)
        self._entries_treeview.set_model(self._entries_treestore)

        self.storage = None
        self.model = storepass.model.Model()

    def run_default_actions(self):
        # Try to open the default password database.
        default_database = os.path.join(os.path.expanduser('~'),
                                        '.storepass.db')
        if os.path.exists(default_database):
            self._open_password_database(default_database)

    def _clear_state(self):
        """Clear the current state. The result is a blank database."""

        self.storage = None
        self.model = None
        self._entries_treestore.clear()

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
        """

        dialog = Gtk.FileChooserDialog(
            "Open File", self, Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK,
             Gtk.ResponseType.OK), modal=True)
        dialog.connect('response', self._on_open_dialog_response)
        dialog.show()

    def _on_open_dialog_response(self, dialog, response_id):
        if response_id != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        filename = dialog.get_filename()
        dialog.destroy()

        self._open_password_database(filename)

    def _open_password_database(self, filename):
        self._clear_state()

        # Ask for the password via a dialog.
        dialog = _PasswordDialog(self, filename)
        dialog.connect('response',
                       self._on_open_password_database_dialog_response)
        dialog.show()
        dialog.present_with_time(Gdk.CURRENT_TIME)

    def _on_open_password_database_dialog_response(self, dialog, response_id):
        assert isinstance(dialog, _PasswordDialog)

        if response_id != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        filename = dialog.get_filename()
        password = dialog.get_password()
        dialog.destroy()
        self._open_password_database2(filename, password)

    def _open_password_database2(self, filename, password):
        # TODO Error checking.
        self.storage = storepass.storage.Storage(filename, password)
        self.model = storepass.model.Model()
        self.model.load(self.storage)

        self._populate_treeview()

    def _on_save(self, action, param):
        """
        Handle the Save action which is used to store the currently opened
        password database on disk.
        """

        # Redirect to the Save As action if this is a new database and its
        # filename has not been specified yet.
        if self.storage is None:
            self._on_save_as(action, param)
            return

        self.model.save(self.storage)

    def _on_save_as(self, action, param):
        """
        Handle the Save As action which is used to store the currently opened
        password database on disk under a new name.
        """

        dialog = Gtk.FileChooserDialog(
            "Save As", self, Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK,
                Gtk.ResponseType.OK), modal=True)
        dialog.connect('response', self._on_save_as_dialog_response)
        dialog.show()

    def _on_save_as_dialog_response(self, dialog, response_id):
        if response_id != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        filename = dialog.get_filename()
        dialog.destroy()

        if self.storage is not None:
            self._save_as_password_database2(filename, self.storage.password)
        else:
            self._save_as_password_database(filename)

    def _save_as_password_database(self, filename):
        # Ask for the password via a dialog.
        dialog = _PasswordDialog(self, filename)
        dialog.connect('response',
                       self._on_save_password_database_dialog_response)
        dialog.show()
        dialog.present_with_time(Gdk.CURRENT_TIME)

    def _on_save_password_database_dialog_response(self, dialog, response_id):
        assert isinstance(dialog, _PasswordDialog)

        if response_id != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        filename = dialog.get_filename()
        password = dialog.get_password()
        dialog.destroy()

        self._save_as_password_database2(filename, password)

    def _save_as_password_database2(self, filename, password):
        self.storage = storepass.storage.Storage(filename, password)
        self.model.save(self.storage)

    def _populate_treeview(self):
        self.model.visit_all(TreeStorePopulator(self._entries_treestore))

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

    @Gtk.Template.Callback("on_entries_treeview_selection_changed")
    def _on_entries_treeview_selection_changed(self, tree_selection):
        model, entry_iter = tree_selection.get_selected()
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

        entry = model.get_value(entry_iter,
                                ENTRIES_TREEVIEW_ENTRY_COLUMN).entry

        # Show the panel with details of the entry.
        self._update_entry_property(self._entry_name_box,
                                    self._entry_name_label, entry.name, False)
        self._update_entry_property(self._entry_description_box,
                                    self._entry_description_label,
                                    entry.description, False)
        # TODO Convert datetime to a string.
        #self._update_entry_property(
        #    self._entry_updated_box, self._entry_updated_label, entry.updated,
        #    False)
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


class _App(Gtk.Application):
    def __init__(self):
        super().__init__()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        menu_xml = importlib.resources.read_text('storepass.gtk.resources',
                                                 'main_menu.ui')
        builder = Gtk.Builder.new_from_string(menu_xml, -1)
        self.set_menubar(builder.get_object("main-menu"))

    def do_activate(self):
        window = _MainWindow(self)
        window.show()
        window.run_default_actions()

    def _on_quit(self, action, param):
        self.quit()

    def _on_about(self, action, param):
        print("_on_about")


def main():
    app = _App()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
