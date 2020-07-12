# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Textual views suitable for the console."""

import storepass.model


class ListView(storepass.model.ModelVisitor):
    """View that produces a tree with one-line about each visited entry."""
    def visit_root(self, root):
        """Process the database root."""
        # Do nothing.

    def _get_current_indent(self):
        """Obtain current indentation."""
        return "  " * (len(self._path) - 1)

    def _format_address(self, hostname):
        """Prepare an address string."""
        return f" [{hostname}]" if hostname is not None else ""

    def _format_description(self, description):
        """Prepare a description string."""
        return f": {description}" if description is not None else ""

    def visit_folder(self, folder):
        """Print one-line information about a folder entry."""
        indent = self._get_current_indent()
        description = self._format_description(folder.description)
        print(f"{indent}+ {folder.name}{description}")

    def visit_credit_card(self, credit_card):
        """Print one-line information about a credit-card entry."""
        indent = self._get_current_indent()
        description = self._format_description(credit_card.description)
        print(f"{indent}- {credit_card.name}{description}")

    def visit_crypto_key(self, crypto_key):
        """Print one-line information about a crypto-key entry."""
        indent = self._get_current_indent()
        address = self._format_address(crypto_key.hostname)
        description = self._format_description(crypto_key.description)
        print(f"{indent}- {crypto_key.name}{address}{description}")

    def visit_database(self, database):
        """Print one-line information about a database entry."""
        indent = self._get_current_indent()
        address = self._format_address(database.hostname)
        description = self._format_description(database.description)
        print(f"{indent}- {database.name}{address}{description}")

    def visit_door(self, door):
        """Print one-line information about a door entry."""
        indent = self._get_current_indent()
        description = self._format_description(door.description)
        print(f"{indent}- {door.name}{description}")

    def visit_email(self, email):
        """Print one-line information about an email entry."""
        indent = self._get_current_indent()
        address = self._format_address(email.hostname)
        description = self._format_description(email.description)
        print(f"{indent}- {email.name}{address}{description}")

    def visit_ftp(self, ftp):
        """Print one-line information about an FTP entry."""
        indent = self._get_current_indent()
        address = self._format_address(ftp.hostname)
        description = self._format_description(ftp.description)
        print(f"{indent}- {ftp.name}{address}{description}")

    def visit_generic(self, generic):
        """Print one-line information about a generic account entry."""
        indent = self._get_current_indent()
        address = self._format_address(generic.hostname)
        description = self._format_description(generic.description)
        print(f"{indent}- {generic.name}{address}{description}")

    def visit_phone(self, phone):
        """Print one-line information about a phone entry."""
        indent = self._get_current_indent()
        description = self._format_description(phone.description)
        print(f"{indent}- {phone.name}{description}")

    def visit_shell(self, shell):
        """Print one-line information about a shell entry."""
        indent = self._get_current_indent()
        address = self._format_address(shell.hostname)
        description = self._format_description(shell.description)
        print(f"{indent}- {shell.name}{address}{description}")

    def visit_remote_desktop(self, remote_desktop):
        """Print one-line information about a remote-desktop entry."""
        indent = self._get_current_indent()
        address = self._format_address(remote_desktop.hostname)
        description = self._format_description(remote_desktop.description)
        print(f"{indent}- {remote_desktop.name}{address}{description}")

    def visit_vnc(self, vnc):
        """Print one-line information about a VNC entry."""
        indent = self._get_current_indent()
        address = self._format_address(vnc.hostname)
        description = self._format_description(vnc.description)
        print(f"{indent}- {vnc.name}{address}{description}")

    def visit_website(self, website):
        """Print one-line information about a website entry."""
        indent = self._get_current_indent()
        address = self._format_address(website.url)
        description = self._format_description(website.description)
        print(f"{indent}- {website.name}{address}{description}")


class DetailView(storepass.model.ModelVisitor):
    """View that shows detailed information about visited entries."""
    def _print_common_info(self, entry):
        """Process common entry properties and print their values."""
        if entry.description is not None:
            print(f"  - Description: {entry.description}")
        if entry.updated is not None:
            updated = entry.updated.astimezone().strftime('%c %Z')
            print(f"  - Last modified: {updated}")
        if entry.notes is not None:
            print(f"  - Notes: {entry.notes}")

    def visit_folder(self, folder):
        """Print detailed information about a folder entry."""
        print(f"+ {folder.get_full_name()} ({folder.ENTRY_LABEL})")
        self._print_common_info(folder)

    def visit_account(self, account):
        """Print detailed information about an account entry."""
        print(f"+ {account.get_full_name()} ({account.ENTRY_LABEL})")
        for field in account.ENTRY_FIELDS:
            value = account.properties[field]
            if value is not None:
                print(f"  - {field.label}: {value}")
        self._print_common_info(account)
