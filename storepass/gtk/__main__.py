# Copyright (C) 2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""StorePass graphical interface built with the GTK library."""

import enum
import importlib.resources
import os
import sys

import gi
gi.require_version('Gdk', '3.0')  # pylint: disable=wrong-import-position
gi.require_version('Gtk', '3.0')  # pylint: disable=wrong-import-position
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import GdkPixbuf
try:
    from gi.repository import GdkX11
    IS_GDK_X11_AVAILABLE = True
except ImportError:
    IS_GDK_X11_AVAILABLE = False
from gi.repository import Gtk

import storepass.exc
import storepass.model
import storepass.storage
from storepass.gtk import edit
from storepass.gtk import utils


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources',
                                  'password_dialog.ui'))
class _PasswordDialog(Gtk.Dialog):
    """Dialog to prompt the user for a database password."""

    __gtype_name__ = 'PasswordDialog'

    _password_entry = Gtk.Template.Child('password_entry')

    def __init__(self, parent_window):
        """Initialize a password dialog."""
        super().__init__(parent=parent_window)

        # Hint correct types to pylint.
        self._password_entry = utils.Hint.GtkEntry(self._password_entry)

    def get_password(self):
        """Return a password input by the user."""
        return self._password_entry.get_text()


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources',
                                  'about_dialog.ui'))
class _AboutDialog(Gtk.AboutDialog):
    """About application dialog."""

    __gtype_name__ = 'AboutDialog'


# Note: Keep these constants in sync with main_window.ui.
class _EntriesTreeStoreColumn(enum.IntEnum):
    """Column IDs in Gtk.TreeStore for the entries tree view."""
    NAME = 0
    ENTRY = 1


class _EntryGObject(GObject.Object):
    """Wrapper of storepass.model.Entry in GObject.Object."""
    def __init__(self, entry):
        super().__init__()
        self.entry = entry


class EntriesTreeStorePopulator(storepass.model.ModelVisitor):
    """Model visitor that populates Gtk.TreeStore for the entries tree view."""
    def __init__(self, tree_store):
        """Initialize a populator for the entries tree view."""
        super().__init__()
        self._tree_store = tree_store

    def visit_root(self, root):
        """Add the database root to the tree."""
        return self._tree_store.append(
            None,
            ["Password Database", _EntryGObject(root)])

    def visit_entry(self, entry):
        """Add a database entry to the tree."""
        parent_iter = self.get_path_data(entry.parent)
        return self._tree_store.append(
            parent_iter, [entry.name, _EntryGObject(entry)])


class EntriesTreeStore(Gtk.TreeStore, Gtk.TreeDragSource, Gtk.TreeDragDest):
    """
    Entries tree store based on Gtk.TreeStore with drag-and-drop upcalls.

    Wrapper for Gtk.TreeStore to allow implementing the Gtk.TreeDragSource and
    Gtk.TreeDragDest interfaces at the same logical level where the TreeStore
    is allocated.
    """
    def __init__(self, column_types, do_drag_data_delete, do_drag_data_get,
                 do_row_draggable, do_drag_data_received,
                 do_row_drop_possible):
        """Initialize an entries tree store and its drag-and-drop callbacks."""
        super().__init__(*column_types)
        self._do_drag_data_delete = do_drag_data_delete
        self._do_drag_data_get = do_drag_data_get
        self._do_row_draggable = do_row_draggable
        self._do_drag_data_received = do_drag_data_received
        self._do_row_drop_possible = do_row_drop_possible

    def do_drag_data_delete(self, path):
        """Override for Gtk.TreeDragSource.do_drag_data_delete()."""
        return self._do_drag_data_delete(self, path)

    def do_drag_data_get(self, path, selection_data):
        """Override for Gtk.TreeDragSource.do_drag_data_get()."""
        return self._do_drag_data_get(self, path, selection_data)

    def do_row_draggable(self, path):
        """Override for Gtk.TreeDragSource.do_row_draggable()."""
        return self._do_row_draggable(self, path)

    def do_drag_data_received(self, dest_path, selection_data):
        """Override for Gtk.TreeDragDest.do_drag_data_received()."""
        return self._do_drag_data_received(self, dest_path, selection_data)

    def do_row_drop_possible(self, dest_path, selection_data):
        """Override for Gtk.TreeDragDest.do_row_drop_possible()."""
        return self._do_row_drop_possible(self, dest_path, selection_data)


@Gtk.Template.from_string(
    importlib.resources.read_text('storepass.gtk.resources', 'main_window.ui'))
class _MainWindow(Gtk.ApplicationWindow):
    """Main application window."""

    __gtype_name__ = 'MainWindow'

    _entries_tree_view = Gtk.Template.Child('entries_tree_view')
    _entries_tree_view_column = Gtk.Template.Child('entries_tree_view_column')
    _entries_tree_view_icon_renderer = Gtk.Template.Child(
        'entries_tree_view_icon_renderer')
    _details_box = Gtk.Template.Child('details_box')
    _db_filename_box = Gtk.Template.Child('db_filename_box')
    _db_filename_label = Gtk.Template.Child('db_filename_label')
    _entry_name_type_box = Gtk.Template.Child('entry_name_type_box')
    _entry_name_type_label = Gtk.Template.Child('entry_name_type_label')
    _entry_description_box = Gtk.Template.Child('entry_description_box')
    _entry_description_label = Gtk.Template.Child('entry_description_label')
    _entry_notes_box = Gtk.Template.Child('entry_notes_box')
    _entry_notes_label = Gtk.Template.Child('entry_notes_label')
    _entry_updated_box = Gtk.Template.Child('entry_updated_box')
    _entry_updated_label = Gtk.Template.Child('entry_updated_label')

    def __init__(self, application):
        """Initialize a main application window."""
        super().__init__(application=application)

        # Hint correct types to pylint.
        self._entries_tree_view = utils.Hint.GtkTreeView(
            self._entries_tree_view)
        self._entries_tree_view_column = utils.Hint.GtkTreeViewColumn(
            self._entries_tree_view_column)
        self._entries_tree_view_icon_renderer = \
            utils.Hint.GtkCellRendererPixbuf(
                self._entries_tree_view_icon_renderer)
        self._details_box = utils.Hint.GtkBox(self._details_box)
        self._db_filename_box = utils.Hint.GtkBox(self._db_filename_box)
        self._db_filename_label = utils.Hint.GtkLabel(self._db_filename_label)
        self._entry_name_type_box = utils.Hint.GtkBox(
            self._entry_name_type_box)
        self._entry_name_type_label = utils.Hint.GtkLabel(
            self._entry_name_type_label)
        self._entry_description_box = utils.Hint.GtkBox(
            self._entry_description_box)
        self._entry_description_label = utils.Hint.GtkLabel(
            self._entry_description_label)
        self._entry_notes_box = utils.Hint.GtkBox(self._entry_notes_box)
        self._entry_notes_label = utils.Hint.GtkLabel(self._entry_notes_label)
        self._entry_updated_box = utils.Hint.GtkBox(self._entry_updated_box)
        self._entry_updated_label = utils.Hint.GtkLabel(
            self._entry_updated_label)

        # Initialize a list to record dynamically created property widgets.
        self._property_boxes = []

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

        # Register an icon mapping function for the entries tree view.
        self._entries_tree_view_column.set_cell_data_func(
            self._entries_tree_view_icon_renderer, self._map_entry_icon)

        # Set up drag-and-drop for the entries tree view.
        target_list = [('GTK_TREE_MODEL_ROW', Gtk.TargetFlags.SAME_WIDGET, 0)]
        self._entries_tree_view.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK, target_list, Gdk.DragAction.MOVE)
        self._entries_tree_view.enable_model_drag_dest(target_list,
                                                       Gdk.DragAction.MOVE)

        menu_xml = importlib.resources.read_text('storepass.gtk.resources',
                                                 'entries_tree_view_menu.ui')
        builder = Gtk.Builder.new_from_string(menu_xml, -1)
        self._entries_tree_view_menu = Gtk.Menu.new_from_model(
            builder.get_object('entries_tree_view_menu'))
        self._entries_tree_view_menu.attach_to_widget(self._entries_tree_view)
        self._entries_tree_view_menu_row_ref = None
        self._entries_tree_view_menu.connect(
            'selection-done', self._on_entries_tree_view_menu_selection_done)

        # Connect context menu actions for the entries tree view.
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

        # "Declare" object's variables. Actual initial values are set in
        # _clear_state() -> _set_new_database().
        self._storage = None
        self._model = None
        self._has_unsaved_changes = False

        # Create an empty database storage and model.
        self._clear_state()

    def _clear_state(self):
        """Reset the current state and create an empty database."""
        storage = storepass.storage.Storage(None, None)
        model = storepass.model.Model()
        self._set_new_database(storage, model)

    def _set_new_database(self, storage, model):
        """Set a new storage + model and prepare the UI for the new model."""
        self._storage = storage
        self._model = model
        self._has_unsaved_changes = False

        # Initialize a new GTK TreeStore model matching the StorePass model and
        # register drag-and-drop support.
        #
        # Note that GTK provides two interfaces that can be used for
        # drag-and-drop in the entries tree view. The low-level one is at the
        # Gtk.Widget level and involves the drag-data-get and
        # drag-data-received signals. The higher-level one is at the
        # Gtk.TreeStore level and relies on the Gtk.TreeDragSource and
        # Gtk.TreeDragDest interfaces.
        #
        # Unfortunately, both these ways are somewhat akward to use in
        # StorePass, due to some limitations. The code then opts for using the
        # higher-level interface but wires the Gtk.TreeDrag(Source|Dest)
        # interfaces to hook them to callbacks in this class, so the code can
        # update both Gtk.TreeStore and StorePass models at the same time.
        tree_store = EntriesTreeStore(
            (str, _EntryGObject), self._entries_tree_store_do_drag_data_delete,
            self._entries_tree_store_do_drag_data_get,
            self._entries_tree_store_do_row_draggable,
            self._entries_tree_store_do_drag_data_received,
            self._entries_tree_store_do_row_drop_possible)
        tree_store.set_sort_column_id(_EntriesTreeStoreColumn.NAME,
                                      Gtk.SortType.ASCENDING)
        self._entries_tree_view.set_model(tree_store)
        self._model.visit_all(EntriesTreeStorePopulator(tree_store))

        # Expand the root node.
        root_iter = tree_store.get_iter_first()
        assert root_iter is not None
        self._entries_tree_view.expand_row(tree_store.get_path(root_iter),
                                           False)

        self._update_title()

    def run_default_actions(self):
        """Run preset actions when the window gets constructed and shown."""
        # Try to open the default password database.
        default_database = os.path.join(os.path.expanduser('~'),
                                        '.storepass.db')
        if not os.path.exists(default_database):
            return

        # Consider opening of the default database as a user activity in the
        # main window and reflect it in the _NET_WM_USER_TIME application
        # window property.
        #
        # This avoids a focus issue during the start-up when the application
        # first displays the main window followed by immediately showing a
        # password dialog. Without adjusting _NET_WM_USER_TIME, it is possible
        # that the main window ends up being wrongly focused instead of the
        # dialog.
        #
        # The problem occurs with some window managers (namely Openbox) when
        # the application is started from a terminal. In such a case, no
        # DESKTOP_STARTUP_ID environment variable is set which results in
        # _NET_WM_USER_TIME for the main window initially getting set to 0 by
        # GTK. When a password dialog then tries to steal the focus, a window
        # manager can consider the no-activity in the main window as if no
        # window that the application has is used and disallows the dialog from
        # getting the focus.
        if IS_GDK_X11_AVAILABLE:
            gdk_window = self.get_window()
            if isinstance(gdk_window, GdkX11.X11Window):
                gdk_window.set_user_time(
                    GdkX11.x11_get_server_time(gdk_window))

        self._open_password_database(default_database)

    def _safe_get_tree_model_iter(self, tree_model, path):
        """Get an iterator from a path, or None if the path does not exist."""
        try:
            return tree_model.get_iter(path)
        except ValueError:
            return None

    def _entries_tree_store_do_drag_data_delete(self, tree_store, path):
        """Handle a drag-and-drop callback to delete a specified entry row."""
        assert tree_store == self._entries_tree_view.get_model()

        # A moved row should be already removed from its original position in
        # _entries_tree_store_do_drag_data_received().
        iter_ = self._safe_get_tree_model_iter(tree_store, path)
        assert iter_ is None
        return False

    def _entries_tree_store_do_drag_data_get(self, tree_store, path,
                                             selection_data):
        """
        Handle a drag-and-drop callback to get data for a specified entry row.

        Fill in selection_data with a GTK_TREE_MODEL_ROW representation of the
        entries-tree-store row at a specified path.
        """
        assert tree_store == self._entries_tree_view.get_model()
        return Gtk.tree_set_row_drag_data(selection_data, tree_store, path)

    def _entries_tree_store_do_row_draggable(self, tree_store, path):
        """
        Handle a drag-and-drop callback to query if an entry row is draggable.

        Return whether a particular entries-tree-store row can be used as the
        source of a drag-and-drop operation.
        """
        assert tree_store == self._entries_tree_view.get_model()

        # Make all entries draggable with the exception of the Root node.
        root_iter = tree_store.get_iter_first()
        assert root_iter is not None
        return path != tree_store.get_path(root_iter)

    def _entries_tree_store_do_drag_data_received(self, tree_store, dest_path,
                                                  selection_data):
        """
        Handle a drag-and-drop callback to insert an entry row.

        Insert an entries-tree-store row before a specified path.
        """
        assert tree_store == self._entries_tree_view.get_model()

        # Get information about the source.
        valid, source_tree_model, source_path = Gtk.tree_get_row_drag_data(
            selection_data)
        if not valid:
            return False
        assert source_tree_model == tree_store

        # Obtain the source entry.
        source_iter = self._safe_get_tree_model_iter(tree_store, source_path)
        if source_iter is None:
            return False
        source_entry = tree_store.get_value(
            source_iter, _EntriesTreeStoreColumn.ENTRY).entry

        # Obtain the destination entry. Look up the closest parent container.
        if dest_path.get_depth() <= 1:
            return False
        res = dest_path.up()
        assert res is True

        dest_iter = self._safe_get_tree_model_iter(tree_store, dest_path)
        if dest_iter is None:
            return False

        # Note: The following loop can have only one or two iterations. Either
        # dest_iter already points to a parent Container, or if this is a drop
        # on top of a non-Container row (the path is in form "X:0") then
        # dest_iter first points to this node and its parent is then the
        # destination.
        while True:
            dest_entry = tree_store.get_value(
                dest_iter, _EntriesTreeStoreColumn.ENTRY).entry
            if isinstance(dest_entry, storepass.model.Container):
                break

            assert dest_path.get_depth() > 1
            res = dest_path.up()
            assert res is True

            dest_iter = tree_store.iter_parent(dest_iter)
            assert dest_iter is not None

        # Silently bail out if the entry is dropped at the same parent, or is
        # moved on itself or to own child Container.
        source_parent_path = source_path.copy()
        res = source_parent_path.up()
        assert res is True
        if (source_parent_path == dest_path or
                dest_path.compare(source_path) == 0 or
                dest_path.is_descendant(source_path)):
            return False

        # Move the entry. Note that a drag_data_received() handler should
        # strictly speaking make a copy of the dragged item and its source
        # should be then removed by a drag_data_delete() handler. However, this
        # would require excessive copying when a whole subtree is moved. Since
        # the drag-and-drop functionality is in this case limited only to a
        # single widget (the entries tree view), it can be optimized to a move
        # operation.
        try:
            self._model.move_entry(source_entry, dest_entry)
        except storepass.exc.ModelException as e:
            utils.show_error_dialog(self, "Error moving entry", f"{e}.")
            return False

        # Update the GTK model.
        tree_store.remove(source_iter)
        entry_iter = tree_store.append(
            dest_iter,
            [source_entry.name, _EntryGObject(source_entry)])
        if isinstance(source_entry, storepass.model.Folder):
            populator = EntriesTreeStorePopulator(tree_store)
            source_entry.accept_children(populator, entry_iter)

        # Select the newly added entry.
        self._entries_tree_view.expand_to_path(tree_store.get_path(entry_iter))
        tree_selection = self._entries_tree_view.get_selection()
        tree_selection.select_iter(entry_iter)

        self._record_modification()
        return True

    def _entries_tree_store_do_row_drop_possible(self, tree_store, _dest_path,
                                                 _selection_data):
        """
        Handle a drag-and-drop callback to query if an entry row is droppable.

        Return whether a drop of an entries-tree-store row is possible before a
        specified path.
        """
        assert tree_store == self._entries_tree_view.get_model()

        # Allow drops at all rows and instead sort out invalid conditions in
        # _entries_tree_store_do_drag_data_received(). Unfortunately, it does
        # not look possible to limit drops only into Container's. The problem
        # is that while GTK tracks whether a drop is before, after or into a
        # row and this is used for highlighting a drop destination, the
        # information is not available in this function. The passed dest_path
        # value (Gtk.TreePath) conflates the mentioned cases and so limiting
        # the selection using this value always causes accepting at least two
        # drop types and therefore unexpected highlighting.
        #
        # Note also that dest_path does not have to exist. If a drop is on top
        # of a leaf node, the path should contain an extra '0' element to
        # indicate that this is a drop into it, or in other words that this is
        # a drop before the first (non-existent) sub-node of this node. This
        # case is accepted as such.
        return True

    def _get_db_filename(self):
        """Return a database filename, or "<unsaved>" if not yet saved."""
        return (self._storage.filename
                if self._storage.filename is not None else "<unsaved>")

    def _update_title(self):
        """
        Update the window title to reflect a modified state.

        Update the window title. This method should be called every time when
        the database filename is changed or the self._has_unsaved_changes flag
        changes its state.
        """
        unsaved_flag = "*" if self._has_unsaved_changes else ""
        filename = self._get_db_filename()
        self.set_title(f"{unsaved_flag}{filename} - StorePass")

    def _record_modification(self):
        """
        Record and react to a database modification by the user.

        Record that the database has been modified since the last save and
        update the window title.
        """
        if self._has_unsaved_changes:
            return

        self._has_unsaved_changes = True
        self._update_title()

    def _map_entry_icon(self, tree_column, cell, tree_model, iter_, _data):
        """Set an icon name for a specified row in the entries tree view."""
        assert tree_column == self._entries_tree_view_column
        assert cell == self._entries_tree_view_icon_renderer
        assert tree_model == self._entries_tree_view.get_model()

        # Set an icon based on the entry type.
        entry = tree_model.get_value(iter_,
                                     _EntriesTreeStoreColumn.ENTRY).entry
        if isinstance(entry, storepass.model.Root):
            cell.props.icon_name = 'x-office-address-book'
        elif isinstance(entry, storepass.model.Folder):
            cell.props.icon_name = 'folder'
        else:
            cell.props.icon_name = 'x-office-document'

    def _on_new(self, _action, _param):
        """Handle the new action: create a new password database."""
        self._clear_state()

    def _on_open(self, _action, _param):
        """
        Handle the open action: open an existing password database.

        Handle the open action by performing the following steps:
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
        """Process a response from a file-open dialog."""
        assert isinstance(dialog, Gtk.FileChooserDialog)

        if response_id != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        filename = dialog.get_filename()
        dialog.destroy()

        # Continue the process of opening the file.
        self._open_password_database(filename)

    def _open_password_database(self, filename):
        """
        Open a password database specified by a filename.

        Open a password database specified by a filename after prompting for
        its master password via a dialog.
        """
        self._clear_state()

        # Ask for the password via a dialog.
        dialog = _PasswordDialog(self)
        dialog.connect('response',
                       self._on_open_password_database_dialog_response,
                       filename)
        dialog.show()

    def _on_open_password_database_dialog_response(self, dialog, response_id,
                                                   filename):
        """Process a response from a password dialog, for database open."""
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
        Complete the process of opening a password database.

        Load a password database specified by a filename and its master
        password into the program.
        """
        storage = storepass.storage.Storage(filename, password)
        model = storepass.model.Model()

        try:
            model.load(storage)
        except storepass.exc.StorageReadException as e:
            utils.show_error_dialog(
                self, "Error loading password database",
                f"Failed to load password database '{filename}': {e}.")
            return

        self._set_new_database(storage, model)

    def _on_save(self, action, param):
        """Handle the save action: save the current password database."""
        # Redirect to the save-as action if this is a new database and its
        # filename has not been specified yet.
        if self._storage.filename is None:
            self._on_save_as(action, param)
            return

        try:
            self._model.save(self._storage)
        except storepass.exc.StorageWriteException as e:
            filename = self._storage.filename
            utils.show_error_dialog(
                self, "Error saving password database",
                f"Failed to save password database '{filename}': {e}.")
            return

        self._has_unsaved_changes = False
        self._update_title()

    def _on_save_as(self, _action, _param):
        """
        Handle the save-as action: save-as the current password database.

        Handle the save-as action by performing the following steps:
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
        """Process a response from a save-as dialog."""
        assert isinstance(dialog, Gtk.FileChooserDialog)

        if response_id != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        filename = dialog.get_filename()
        dialog.destroy()

        # Continue the process of saving the file. If the database already has
        # a password specified then proceed to saving it, else first prompt for
        # the password.
        if self._storage.password is not None:
            self._save_as_password_database2(filename, self._storage.password)
        else:
            self._save_as_password_database(filename)

    def _save_as_password_database(self, filename):
        """
        Save a password database to a specified file.

        Save a password database to a specified file after prompting for its
        master password via a dialog.
        """
        # Ask for the password via a dialog.
        dialog = _PasswordDialog(self)
        dialog.connect('response',
                       self._on_save_password_database_dialog_response,
                       filename)
        dialog.show()

    def _on_save_password_database_dialog_response(self, dialog, response_id,
                                                   filename):
        """Process a response from a password dialog, for database save."""
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
        Complete the process of saving a password database.

        Save a password database specified by a filename and its master
        password.
        """
        storage = storepass.storage.Storage(filename, password)

        try:
            self._model.save(storage)
        except storepass.exc.StorageWriteException as e:
            utils.show_error_dialog(
                self, "Error saving password database",
                f"Failed to save password database '{filename}': {e}.")
            return

        self._storage = storage

        self._has_unsaved_changes = False
        self._update_title()

    def _update_entry_detail_widget_box(self, box_widget, label_widget, text):
        """Set a text in an info-detail box, or hide it if the text is None."""
        if text is not None:
            label_widget.set_text(text)
            box_widget.show()
        else:
            box_widget.hide()
            label_widget.set_text("")

    @Gtk.Template.Callback('on_entries_tree_view_selection_changed')
    def _on_entries_tree_view_selection_changed(self, tree_selection):
        """
        Handle a changed selection in the entries tree view.

        Update the main information panel and display details of a newly
        selected entry.
        """
        tree_store, entry_iter = tree_selection.get_selected()
        entry = tree_store.get_value(
            entry_iter, _EntriesTreeStoreColumn.ENTRY
        ).entry if entry_iter is not None else None

        # Process the entry's name.
        if entry is not None:
            if isinstance(entry, storepass.model.Root):
                name_type = "Password Database"
            elif isinstance(entry, storepass.model.Entry):
                name_type = f"{entry.name} ({entry.entry_label})"
        else:
            name_type = None
        self._update_entry_detail_widget_box(self._entry_name_type_box,
                                             self._entry_name_type_label,
                                             name_type)

        # Handle the root selection by displaying the database filename.
        if entry is not None and isinstance(entry, storepass.model.Root):
            db_filename = self._get_db_filename()
        else:
            db_filename = None
        self._update_entry_detail_widget_box(self._db_filename_box,
                                             self._db_filename_label,
                                             db_filename)

        # Process the entry's description.
        if entry is not None and isinstance(entry, storepass.model.Entry):
            description = entry.description
        else:
            description = None
        self._update_entry_detail_widget_box(self._entry_description_box,
                                             self._entry_description_label,
                                             description)

        # Process entry-specific properties.
        # Destroy any current property widgets.
        for property_box in self._property_boxes:
            self._details_box.remove(property_box)
        self._property_boxes = []

        # Create and insert property widgets for the selected type.
        if entry is not None and isinstance(entry, storepass.model.Entry):
            insert_at = self._details_box.child_get_property(
                self._entry_description_box, 'position') + 1

            for field in entry.entry_fields:
                value = entry.properties[field]
                if value is None:
                    continue

                property_xml = importlib.resources.read_text(
                    'storepass.gtk.resources', 'view_property_widgets.ui')
                builder = Gtk.Builder.new_from_string(property_xml, -1)

                property_box = builder.get_object('property_box')
                self._details_box.add(property_box)
                self._details_box.reorder_child(property_box, insert_at)

                property_name_label = builder.get_object('property_name_label')
                property_name_label.set_text(f"{field.label}: ")

                property_value_label = builder.get_object(
                    'property_value_label')
                property_value_label.set_text(value)

                self._property_boxes.append(property_box)
                insert_at += 1

        # Process the entry's notes.
        if entry is not None and isinstance(entry, storepass.model.Entry):
            notes = entry.notes
        else:
            notes = None
        self._update_entry_detail_widget_box(self._entry_notes_box,
                                             self._entry_notes_label, notes)

        # Process the entry's updated value.
        if entry is not None and isinstance(entry, storepass.model.Entry):
            updated = entry.updated
            if updated is not None:
                updated = updated.astimezone().strftime('%c %Z')
        else:
            updated = None
        self._update_entry_detail_widget_box(self._entry_updated_box,
                                             self._entry_updated_label,
                                             updated)

    @Gtk.Template.Callback('on_entries_tree_view_button_press_event')
    def _on_entries_tree_view_button_press_event(self, widget, event):
        """
        Handle a button/mouse press event inside the entries tree view.

        Display an entry context menu if the right mouse button was pressed
        inside the entries tree view on top of some entry row.
        """
        assert widget == self._entries_tree_view

        # Ignore events that are not a right mouse button press.
        if (event.type != Gdk.EventType.BUTTON_PRESS or
                event.button != Gdk.BUTTON_SECONDARY):
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
        Handle a completed selection in the entries tree view menu.

        Reset the current tree view row reference after a completed selection
        in the tree view menu. This provides accurate tracking by the
        _entries_tree_view_menu_row_ref variable.

        Note that the selection-done signal is emitted after a menu action is
        performed and the signal is invoked even if the menu was cancelled.
        """
        assert menu_shell == self._entries_tree_view_menu
        self._entries_tree_view_menu_row_ref = None

    def _unwrap_entries_tree_row_reference(self, tree_row_ref):
        """
        Get a model, an iterator and an entry from a specified row reference.

        Obtain a model that a specified row reference is currently monitoring,
        an iterator that the reference points to and an actual entry object.
        The row reference must be valid.
        """
        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        model = tree_row_ref.get_model()
        iter_ = model.get_iter(tree_row_ref.get_path())
        entry = model.get_value(iter_, _EntriesTreeStoreColumn.ENTRY).entry
        return model, iter_, entry

    def _get_entries_tree_view_menu_associated_entry(self, get_container):
        """
        Obtain an entry currently associated with the entries tree view menu.

        Obtain an entry associated with the currently opened entries tree view
        menu. If get_container is True and the entry is not a Container then
        look up and return its parent.
        """
        assert self._entries_tree_view_menu_row_ref is not None
        assert self._entries_tree_view_menu_row_ref.valid()

        # Get the selected entry.
        tree_row_ref = self._entries_tree_view_menu_row_ref
        tree_store, entry_iter, entry = \
            self._unwrap_entries_tree_row_reference(tree_row_ref)
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
        """
        Replace an existing entry in the model with a new one.

        Replace an existing entry in the model that is associated with a
        specified row reference with a new entry. Returns True if the the entry
        has been successfully updated, otherwise an error dialog is displayed
        and False is returned.
        """
        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        tree_store, entry_iter, old_entry = \
            self._unwrap_entries_tree_row_reference(tree_row_ref)
        assert tree_store == self._entries_tree_view.get_model()

        try:
            self._model.replace_entry(old_entry, new_entry)
        except storepass.exc.ModelException as e:
            utils.show_error_dialog(self, "Error updating entry", f"{e}.")
            return False

        # Update the GTK model.
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

        self._record_modification()
        return True

    def _on_edit_entry(self, _action, _param):
        """Handle the edit-entry action: start an entry modification."""
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
        """Process a response from an edit-database dialog."""
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
        """Process a response from an edit-folder dialog."""
        assert isinstance(dialog, edit.EditFolderDialog)
        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        if response_id != Gtk.ResponseType.APPLY:
            dialog.destroy()
            return

        # Obtain the newly defined folder and replace the old one.
        new_entry = dialog.get_entry()
        if not self._replace_entry(tree_row_ref, new_entry):
            return

        dialog.destroy()

    def _on_edit_account_dialog_response(self, dialog, response_id,
                                         tree_row_ref):
        """Process a response from an edit-account dialog."""
        assert isinstance(dialog, edit.EditAccountDialog)
        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        if response_id != Gtk.ResponseType.APPLY:
            dialog.destroy()
            return

        # Obtain the newly defined account and replace the old one.
        new_entry = dialog.get_entry()
        if not self._replace_entry(tree_row_ref, new_entry):
            return

        dialog.destroy()

    def _remove_entry(self, tree_row_ref):
        """
        Remove an entry from the model.

        Remove an entry that is associated with a specified row reference from
        the model. If the entry is the Root then the whole database is cleared.
        """
        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        tree_store, entry_iter, entry = \
            self._unwrap_entries_tree_row_reference(tree_row_ref)

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

        self._record_modification()

    def _on_remove_confirmation_dialog_response(self, dialog, response_id,
                                                tree_row_ref):
        """Process a response from a dialog to confirm removal of an entry."""
        # Remove the entry if the user confirmed the operation.
        if response_id == Gtk.ResponseType.OK:
            self._remove_entry(tree_row_ref)

        dialog.destroy()

    def _on_remove_entry(self, _action, _param):
        """Handle the remove-entry action: remove an existing entry."""
        # Get the selected entry (do not require a Container).
        tree_row_ref, entry = \
            self._get_entries_tree_view_menu_associated_entry(False)

        # Remove the entry. However, if it is a Container that is not empty
        # then first prompt the user for a confirmation of the removal.
        if isinstance(entry, storepass.model.Root) and len(entry.children) > 0:
            utils.show_confirmation_dialog(
                self, "Remove all entries",
                "Operation will remove all entries from the database.",
                "Remove", self._on_remove_confirmation_dialog_response,
                tree_row_ref)
        elif (isinstance(entry, storepass.model.Folder) and
              len(entry.children) > 0):
            utils.show_confirmation_dialog(
                self, "Remove a non-empty folder",
                f"Folder '{entry.name}' is not empty.", "Remove",
                self._on_remove_confirmation_dialog_response, tree_row_ref)
        else:
            self._remove_entry(tree_row_ref)

    def _add_entry(self, tree_row_ref, new_entry):
        """
        Add a new entry in the model.

        Add a new entry in the model under a parent entry that is associated
        with a specified row reference. Returns True if the new entry has been
        successfully added, otherwise an error dialog is displayed and False is
        returned.
        """
        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        tree_store, parent_iter, parent_entry = \
            self._unwrap_entries_tree_row_reference(tree_row_ref)
        assert tree_store == self._entries_tree_view.get_model()

        try:
            self._model.add_entry(new_entry, parent_entry)
        except storepass.exc.ModelException as e:
            utils.show_error_dialog(self, "Error adding entry", f"{e}.")
            return False

        # Update the GTK model.
        entry_iter = tree_store.append(
            parent_iter,
            [new_entry.name, _EntryGObject(new_entry)])

        # Select the newly added entry.
        self._entries_tree_view.expand_to_path(tree_store.get_path(entry_iter))
        tree_selection = self._entries_tree_view.get_selection()
        tree_selection.select_iter(entry_iter)

        self._record_modification()
        return True

    def _on_add_folder(self, _action, _param):
        """Handle the add-folder action: start adding a new folder."""
        # Get the selected entry (lookup the closest Container).
        tree_row_ref, _entry = \
            self._get_entries_tree_view_menu_associated_entry(True)

        dialog = edit.EditFolderDialog(self, None)
        dialog.connect('response', self._on_add_folder_dialog_response,
                       tree_row_ref)
        dialog.show()

    def _on_add_folder_dialog_response(self, dialog, response_id,
                                       tree_row_ref):
        """Process a response from an add-folder dialog."""
        assert isinstance(dialog, edit.EditFolderDialog)
        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        if response_id != Gtk.ResponseType.APPLY:
            dialog.destroy()
            return

        # Obtain the newly defined folder and add it.
        new_entry = dialog.get_entry()
        if not self._add_entry(tree_row_ref, new_entry):
            return

        dialog.destroy()

    def _on_add_account(self, _action, _param):
        """Handle the add-account action: start adding a new account."""
        # Get the selected entry (lookup the closest Container).
        tree_row_ref, _entry = \
            self._get_entries_tree_view_menu_associated_entry(True)

        dialog = edit.EditAccountDialog(self, None)
        dialog.connect('response', self._on_add_account_dialog_response,
                       tree_row_ref)
        dialog.show()

    def _on_add_account_dialog_response(self, dialog, response_id,
                                        tree_row_ref):
        """Process a response from an add-account dialog."""
        assert isinstance(dialog, edit.EditAccountDialog)
        assert tree_row_ref is not None
        assert tree_row_ref.valid()

        if response_id != Gtk.ResponseType.APPLY:
            dialog.destroy()
            return

        # Obtain the newly defined account and add it.
        new_entry = dialog.get_entry()
        if not self._add_entry(tree_row_ref, new_entry):
            return

        dialog.destroy()


class _App(Gtk.Application):
    """StorePass GTK application."""
    def do_startup(self, *args, **kwargs):
        """Set up the application when it first starts."""
        Gtk.Application.do_startup(self)
        GLib.set_prgname("StorePass")

        # Set the default icon for all windows and for use in the about dialog.
        icon_bytes = importlib.resources.read_binary('storepass.gtk.resources',
                                                     'icon.svg')
        icon_stream = Gio.MemoryInputStream.new_from_bytes(
            GLib.Bytes.new(icon_bytes))
        icon = GdkPixbuf.Pixbuf.new_from_stream(icon_stream, None)
        Gtk.Window.set_default_icon(icon)

        # Initialize main menu.
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

    def do_activate(self, *args, **kwargs):
        """Handle activation of the application by showing its main window."""
        window = _MainWindow(self)
        window.show()
        window.run_default_actions()

    def _on_quit(self, _action, _param):
        """Handle the quit action by exiting the application."""
        self.quit()

    def _on_about(self, _action, _param):
        """Handle the about action by showing the about application dialog."""
        dialog = _AboutDialog()
        dialog.connect('response',
                       lambda dialog, response_id: dialog.destroy())
        dialog.show()


def main():
    """
    Run the GTK interface.

    Run the StorePass graphical interface. Returns 0 if the execution was
    successful and a non-zero value otherwise.
    """
    app = _App()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
