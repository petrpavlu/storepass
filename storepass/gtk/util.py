# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import gi
gi.require_version('Gtk', '3.0')  # pylint: disable=wrong-import-position
from gi.repository import Gtk


def show_error_dialog(parent_window, primary_text, secondary_text):
    """Create and display an error dialog."""

    dialog = Gtk.MessageDialog(
        parent_window,
        Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, primary_text)
    dialog.format_secondary_text(secondary_text)
    dialog.connect('response', lambda dialog, response_id: dialog.destroy())
    dialog.show()


def show_confirmation_dialog(parent_window, primary_text, secondary_text,
                             confirmation_label, response_handler,
                             *response_handler_args):
    """Create and display a confirmation dialog."""

    dialog = Gtk.MessageDialog(
        parent_window,
        Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        Gtk.MessageType.WARNING, Gtk.ButtonsType.NONE, primary_text)
    dialog.format_secondary_text(secondary_text)
    dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, confirmation_label,
                       Gtk.ResponseType.OK)
    dialog.connect('response', response_handler, *response_handler_args)
    dialog.show()


class Hint:
    """Dummy type hints for pylint."""
    @staticmethod
    def GtkBox(child):  # pylint: disable=invalid-name
        """:rtype: Gtk.Box"""
        return child

    @staticmethod
    def GtkButton(child):  # pylint: disable=invalid-name
        """:rtype: Gtk.Button"""
        return child

    @staticmethod
    def GtkCellRendererPixbuf(child):  # pylint: disable=invalid-name
        """:rtype: Gtk.GtkCellRendererPixbuf"""
        return child

    @staticmethod
    def GtkComboBox(child):  # pylint: disable=invalid-name
        """:rtype: Gtk.ComboBox"""
        return child

    @staticmethod
    def GtkEntry(child):  # pylint: disable=invalid-name
        """:rtype: Gtk.Entry"""
        return child

    @staticmethod
    def GtkLabel(child):  # pylint: disable=invalid-name
        """:rtype: Gtk.Label"""
        return child

    @staticmethod
    def GtkTextView(child):  # pylint: disable=invalid-name
        """:rtype: Gtk.TextView"""
        return child

    @staticmethod
    def GtkTreeView(child):  # pylint: disable=invalid-name
        """:rtype: Gtk.TreeView"""
        return child

    @staticmethod
    def GtkTreeViewColumn(child):  # pylint: disable=invalid-name
        """:rtype: Gtk.TextViewColumn"""
        return child
