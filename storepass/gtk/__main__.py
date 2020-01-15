# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import gi
import importlib.resources
import sys

gi.require_version('Gtk', '3.0')
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Gtk


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources', 'main_window.ui'))
class MainWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    hello_world = Gtk.Template.Child()
    entry_treeview = Gtk.Template.Child()

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

        store = Gtk.TreeStore(str)
        store.append(None, ["foo"])
        store.append(None, ["bar"])
        self.entry_treeview.set_model(store)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Title", renderer, text=0)
        self.entry_treeview.append_column(column)
    def on_new(self, action, param):
        print("on_new")

    def on_open(self, action, param):
        print("on_open")

    def on_save(self, action, param):
        print("on_save")

    def on_save_as(self, action, param):
        print("on_save_as")



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
