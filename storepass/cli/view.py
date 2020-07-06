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

    def _print_property(self, name, value):
        """Print a single property."""
        if value is not None:
            print(f"  - {name}: {value}")

    def visit_folder(self, folder):
        """Print detailed information about a folder entry."""
        print(f"+ {folder.name} (folder)")
        self._print_common_info(folder)

    def visit_credit_card(self, credit_card):
        """Print detailed information about a credit-card entry."""
        print(f"+ {credit_card.name} (credit card)")
        self._print_property("Card type", credit_card.card_type)
        self._print_property("Card number", credit_card.card_number)
        self._print_property("Expiry date", credit_card.expiry_date)
        self._print_property("CCV", credit_card.ccv)
        self._print_property("PIN", credit_card.pin)
        self._print_common_info(credit_card)

    def visit_crypto_key(self, crypto_key):
        """Print detailed information about a crypto-key entry."""
        print(f"+ {crypto_key.name} (crypto key)")
        self._print_property("Hostname", crypto_key.hostname)
        self._print_property("Certificate", crypto_key.certificate)
        self._print_property("Keyfile", crypto_key.keyfile)
        self._print_property("Password", crypto_key.password)
        self._print_common_info(crypto_key)

    def visit_database(self, database):
        """Print detailed information about a database entry."""
        print(f"+ {database.name} (database)")
        self._print_property("Hostname", database.hostname)
        self._print_property("Username", database.username)
        self._print_property("Password", database.password)
        self._print_property("Database", database.database)
        self._print_common_info(database)

    def visit_door(self, door):
        """Print detailed information about a door entry."""
        print(f"+ {door.name} (door)")
        self._print_property("Location", door.location)
        self._print_property("Code", door.code)
        self._print_common_info(door)

    def visit_email(self, email):
        """Print detailed information about an email entry."""
        print(f"+ {email.name} (email)")
        self._print_property("Email", email.email)
        self._print_property("Hostname", email.hostname)
        self._print_property("Username", email.username)
        self._print_property("Password", email.password)
        self._print_common_info(email)

    def visit_ftp(self, ftp):
        """Print detailed information about an FTP entry."""
        print(f"+ {ftp.name} (FTP)")
        self._print_property("Hostname", ftp.hostname)
        self._print_property("Port", ftp.port)
        self._print_property("Username", ftp.username)
        self._print_property("Password", ftp.password)
        self._print_common_info(ftp)

    def visit_generic(self, generic):
        """Print detailed information about a generic account entry."""
        print(f"+ {generic.name} (generic account)")
        self._print_property("Hostname", generic.hostname)
        self._print_property("Username", generic.username)
        self._print_property("Password", generic.password)
        self._print_common_info(generic)

    def visit_phone(self, phone):
        """Print detailed information about a phone account entry."""
        print(f"+ {phone.name} (phone)")
        self._print_property("Phone number", phone.phone_number)
        self._print_property("PIN", phone.pin)
        self._print_common_info(phone)

    def visit_shell(self, shell):
        """Print detailed information about a shell account entry."""
        print(f"+ {shell.name} (shell)")
        self._print_property("Hostname", shell.hostname)
        self._print_property("Domain", shell.domain)
        self._print_property("Username", shell.username)
        self._print_property("Password", shell.password)
        self._print_common_info(shell)

    def visit_remote_desktop(self, remote_desktop):
        """Print detailed information about a remote-desktop account entry."""
        print(f"+ {remote_desktop.name} (remote desktop)")
        self._print_property("Hostname", remote_desktop.hostname)
        self._print_property("Port", remote_desktop.port)
        self._print_property("Username", remote_desktop.username)
        self._print_property("Password", remote_desktop.password)
        self._print_common_info(remote_desktop)

    def visit_vnc(self, vnc):
        """Print detailed information about a VNC account entry."""
        print(f"+ {vnc.name} (VNC)")
        self._print_property("Hostname", vnc.hostname)
        self._print_property("Port", vnc.port)
        self._print_property("Username", vnc.username)
        self._print_property("Password", vnc.password)
        self._print_common_info(vnc)

    def visit_website(self, website):
        """Print detailed information about a website account entry."""
        print(f"+ {website.name} (website)")
        self._print_property("URL", website.url)
        self._print_property("Username", website.username)
        self._print_property("Email", website.email)
        self._print_property("Password", website.password)
        self._print_common_info(website)
