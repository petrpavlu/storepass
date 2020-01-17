# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import gi
import importlib.resources
import os
import sys

# TODO Remove.
import getpass

gi.require_version('Gtk', '3.0')
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gtk

import storepass.model
import storepass.storage

# Keep in sync with the ui files.
ENTRIES_TREEVIEW_NAME_COLUMN = 0
ENTRIES_TREEVIEW_ENTRY_COLUMN = 1

class EntryGObject(GObject.Object):
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
        return self.tree_store.append(parent_iter,
            [folder.name, EntryGObject(folder)])

    def visit_generic(self, parent, generic):
        parent_iter = self.get_path_data(parent)
        assert ENTRIES_TREEVIEW_NAME_COLUMN == 0
        assert ENTRIES_TREEVIEW_ENTRY_COLUMN == 1
        return self.tree_store.append(parent_iter,
            [generic.name, EntryGObject(generic)])


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources', 'main_window.ui'))
class MainWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    entries_treeview = Gtk.Template.Child()
    entry_name = Gtk.Template.Child()
    entry_description = Gtk.Template.Child()
    entry_updated = Gtk.Template.Child()
    entry_notes = Gtk.Template.Child()
    entry_stack = Gtk.Template.Child()
    entry_generic_hostname = Gtk.Template.Child()
    entry_generic_username = Gtk.Template.Child()
    entry_generic_password = Gtk.Template.Child()

    def __init__(self, application):
        super().__init__(application=application)

        new_action = Gio.SimpleAction.new("new", None)
        new_action.connect("activate", self.on_new)
        self.add_action(new_action)

        open_action = Gio.SimpleAction.new("open", None)
        open_action.connect("activate", self.on_open)
        self.add_action(open_action)

        save_action = Gio.SimpleAction.new("save", None)
        save_action.connect("activate", self.on_save)
        self.add_action(save_action)

        save_as_action = Gio.SimpleAction.new("save_as", None)
        save_as_action.connect("activate", self.on_save_as)
        self.add_action(save_as_action)

        self._entries_tree_store = Gtk.TreeStore(str, EntryGObject)
        self.entries_treeview.set_model(self._entries_tree_store)

        self.storage = None
        self.model = None
        self._open_default_database()

    def on_new(self, action, param):
        print("on_new")

    def on_open(self, action, param):
        print("on_open")

    def on_save(self, action, param):
        print("on_save")

    def on_save_as(self, action, param):
        print("on_save_as")

    def _open_default_database(self):
        # TODO Ask for the password via a dialog.
        # TODO Check if the file exists first.
        self.storage = storepass.storage.Storage(
            os.path.join(os.path.expanduser('~'), '.storepass.db'),
            getpass.getpass())
        self.model = storepass.model.Model()
        self.model.load(self.storage)

        self._populate_treeview()

    def _populate_treeview(self):
        self.model.visit_all(TreeStorePopulator(self._entries_tree_store))

    def _set_label(self, label_widget, text):
        if text is not None:
            label_widget.set_text(text)
            label_widget.show()
        else:
            label_widget.set_text("")
            label_widget.hide()

    @Gtk.Template.Callback("on_entries_treeview_selection_changed")
    def _on_entries_treeview_selection_changed(self, tree_selection):
        self._set_label(self.entry_name, None)
        self._set_label(self.entry_description, None)
        self._set_label(self.entry_updated, None)
        self._set_label(self.entry_notes, None)

        self.entry_stack.set_visible_child_name("page_empty")
        self._set_label(self.entry_generic_hostname, None)
        self._set_label(self.entry_generic_username, None)
        self._set_label(self.entry_generic_password, None)

        model, entry_iter = tree_selection.get_selected()
        if entry_iter is None:
            return

        entry = model.get_value(entry_iter, ENTRIES_TREEVIEW_ENTRY_COLUMN).entry

        # Show the panel with details of the entry.
        self._set_label(self.entry_name, entry.name)
        self._set_label(self.entry_description, entry.description)
        # TODO Convert datetime to a string.
        #self._set_label(self.entry_updated, entry.updated)
        self._set_label(self.entry_notes, entry.notes)

        if isinstance(entry, storepass.model.Folder):
            self.entry_stack.set_visible_child_name("page_folder")
        elif isinstance(entry, storepass.model.Generic):
            self.entry_stack.set_visible_child_name("page_generic")
            self._set_label(self.entry_generic_hostname, entry.hostname)
            self._set_label(self.entry_generic_username, entry.username)
            self._set_label(self.entry_generic_password, entry.password)
        else:
            self.entry_stack.set_visible_child_name("page_empty")


class App(Gtk.Application):
    def __init__(self):
        super().__init__()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit)
        self.add_action(quit_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)

        menu_xml = importlib.resources.read_text('storepass.gtk.resources',
                                                 'main_menu.ui')
        builder = Gtk.Builder.new_from_string(menu_xml, -1)
        self.set_menubar(builder.get_object("main-menu"))

    def do_activate(self):
        window = MainWindow(self)
        window.show()

    def on_quit(self, action, param):
        self.quit()

    def on_about(self, action, param):
        print("on_about")


def main():
    app = App()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
