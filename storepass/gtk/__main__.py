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

        store = Gtk.TreeStore(str)
        store.append(None, ["foo"])
        store.append(None, ["bar"])
        self.entry_treeview.set_model(store)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Title", renderer, text=0)
        self.entry_treeview.append_column(column)


class App(Gtk.Application):
    def __init__(self):
        super().__init__()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        menu_xml = importlib.resources.read_text('storepass.gtk.resources',
                                                 'main_menu.ui')
        builder = Gtk.Builder.new_from_string(menu_xml, -1)
        self.set_menubar(builder.get_object("main-menu"))

    def do_activate(self):
        window = MainWindow(self)
        window.show()


def main():
    app = App()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
