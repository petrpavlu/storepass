# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import hashlib
import os
import xml.etree.ElementTree as ET
import zlib
from Crypto.Cipher import AES

import storepass.exc
import storepass.model

class _XMLToModelConvertor:
    """XML to internal data model convertor."""

    def __init__(self):
        # Pass as the convertor is stateless.
        pass

    def process(self, xml_data):
        # TODO Implement proper error checking.
        root_elem = ET.fromstring(xml_data)

        return self._parse_root(root_elem)

    def _parse_root(self, xml_elem):
        """Parse the root <revelationdata> element."""

        if xml_elem.tag != 'revelationdata':
            raise storepass.exc.StorageReadException(
                f"Invalid root element '{xml_elem.tag}', expected " \
                f"'revelationdata'")

        # TODO Validate that the element has no unrecognized attributes.

        children = self._parse_subelements(iter(list(xml_elem)))
        return storepass.model.Root(children)

    def _parse_subelements(self, xml_elem_iter):
        """Parse sub-elements of a folder-like element."""

        children = []
        for xml_elem in xml_elem_iter:
            if xml_elem.tag != 'entry':
                raise storepass.exc.StorageReadException(
                    f"Unrecognized element '{xml_elem.tag}', expected 'entry'")

            type_ = xml_elem.get('type')
            if type_ == 'folder':
                folder = self._parse_folder(xml_elem)
                children.append(folder)
            elif type_ == 'generic':
                generic = self._parse_generic(xml_elem)
                children.append(generic)
            else:
                # TODO type_ can be None?
                raise storepass.exc.StorageReadException(
                    f"Unrecognized type attribute '{type_}', expected 'folder' or 'generic'")

        return children

    def _parse_folder(self, xml_elem):
        """Parse a <entry type='folder'> element."""

        assert xml_elem.tag == 'entry'
        assert xml_elem.get('type') == 'folder'

        xml_subelem_iter = iter(list(xml_elem))

        name = None
        description = None
        updated = None
        notes = None

        for xml_subelem in xml_subelem_iter:
            if xml_subelem.tag == 'entry':
                break

            if xml_subelem.tag == 'name':
                name = xml_subelem.text
            elif xml_subelem.tag == 'description':
                description = xml_subelem.text
            elif xml_subelem.tag == 'updated':
                updated = xml_subelem.text
            elif xml_subelem.tag == 'notes':
                notes = xml_subelem.text
            else:
                raise storepass.exc.StorageReadException(
                    f"Unrecognized property element '{xml_subelem.tag}'")

        children = self._parse_subelements(xml_subelem_iter)

        return storepass.model.Folder(name, description, updated, notes,
            children)

    def _parse_generic(self, xml_elem):
        """Parse a <entry type='generic'> element."""

        assert xml_elem.tag == 'entry'
        assert xml_elem.get('type') == 'generic'

        name = None
        description = None
        updated = None
        notes = None
        username = None
        password = None
        hostname = None

        for xml_subelem in list(xml_elem):
            if xml_subelem.tag == 'name':
                name = xml_subelem.text
            elif xml_subelem.tag == 'description':
                description = xml_subelem.text
            elif xml_subelem.tag == 'updated':
                updated = xml_subelem.text
            elif xml_subelem.tag == 'notes':
                notes = xml_subelem.text
            elif xml_subelem.tag == 'field':
                # TODO More checking.
                id_ = xml_subelem.get('id')
                if id_ == 'generic-hostname':
                    hostname = xml_subelem.text
                elif id_ == 'generic-username':
                    username = xml_subelem.text
                elif id_ == 'generic-password':
                    password = xml_subelem.text
                else:
                    # TODO Handle None type.
                    raise storepass.exc.StorageReadException(
                        f"Unrecognized generic id attribute '{id_}'")
            else:
                raise storepass.exc.StorageReadException(
                    f"Unrecognized property element '{xml_subelem.tag}'")

        return storepass.model.Generic(name, description, updated, notes,
           hostname, username, password)

class _ModelToXMLConvertor:
    """Internal data model to XML convertor."""

    def __init__(self):
        self._xml_root = None
        self._parent_chain = []

    def _indent_xml(self, xml_element, level=0):
        """Indent elements of a given ElementTree for pretty-print."""

        indent = '\n' + '\t' * level
        if len(xml_element) > 0:
            xml_element.text = indent + '\t'
            for xml_subelement in xml_element:
                self._indent_xml(xml_subelement, level+1)
            xml_subelement.tail = indent
        xml_element.tail = indent

    def process(self, root):
        """
        Process a password tree structure and return its XML representation (as
        a string).
        """

        self._xml_root = None
        self._parent_chain = []

        # Visit all nodes and create their ElementTree representation.
        root.accept(self)

        # Convert ElementTree representation to a XML document.
        self._indent_xml(self._xml_root)
        data = ET.tostring(self._xml_root, encoding='unicode')

        # Add XML declaration if it is missing.
        # TODO Use xml_declaration=True in Python 3.8.
        if data[:6] != '<?xml ':
            data = '<?xml version="1.0" encoding="utf-8"?>\n' + data

        return data

    def _backtrace_parent(self, parent):
        """
        Pop elements from the parent chain up to the current's node parent.
        """

        assert parent is not None
        assert len(self._parent_chain) > 0

        while self._parent_chain[-1][0] != parent:
            del self._parent_chain[-1]
        return self._parent_chain[-1][1]

    def visit_root(self, parent, root):
        """Create XML representation for the data root."""

        assert parent is None
        assert len(self._parent_chain) == 0

        self._xml_root = ET.Element('revelationdata')
        self._xml_root.set('dataversion', '1')

        self._parent_chain.append((root, self._xml_root))

    def _add_entry_properties(self, entry, xml_entry):
        """Create XML representation for common password entry properties."""

        xml_name = ET.SubElement(xml_entry, 'name')
        xml_name.text = entry.name

        if entry.description is not None:
            xml_description = ET.SubElement(xml_entry, 'description')
            xml_description.text = entry.description

        if entry.updated is not None:
            xml_updated = ET.SubElement(xml_entry, 'updated')
            xml_updated.text = entry.updated

        if entry.notes is not None:
           xml_notes = ET.SubElement(xml_entry, 'notes')
           xml_notes.text = entry.notes

    def visit_folder(self, parent, folder):
        """Create XML representation for a password folder."""

        xml_parent = self._backtrace_parent(parent)

        xml_folder = ET.SubElement(xml_parent, 'entry')
        xml_folder.set('type', 'folder')
        self._add_entry_properties(folder, xml_folder)

        self._parent_chain.append((folder, xml_folder))

    def visit_generic(self, parent, generic):
        """Create XML representation for a generic password record."""

        xml_parent = self._backtrace_parent(parent)

        xml_generic = ET.SubElement(xml_parent, 'entry')
        xml_generic.set('type', 'generic')
        self._add_entry_properties(generic, xml_generic)

        if generic.hostname is not None:
            xml_hostname = ET.SubElement(xml_generic, 'field')
            xml_hostname.set('id', 'generic-hostname')
            xml_hostname.text = generic.hostname

        if generic.username is not None:
            xml_username = ET.SubElement(xml_generic, 'field')
            xml_username.set('id', 'generic-username')
            xml_username.text = generic.username

        if generic.password is not None:
            xml_password = ET.SubElement(xml_generic, 'field')
            xml_password.set('id', 'generic-password')
            xml_password.text = generic.password

class Storage:
    """Password database file reader/writer."""

    def __init__(self, filename, password_proxy):
        self._filename = filename
        self._password_proxy = password_proxy

    def get_password(self):
        if callable(self._password_proxy):
            return self._password_proxy()
        else:
            return self._password_proxy

    def _parse_header(self, header):
        """Verify validity of a password database header."""

        assert len(header) == 12

        if header[:4] != b'rvl\x00':
            raise storepass.exc.StorageReadException(
                f"Invalid magic number, expected b'rvl\\x00' but found "
                f"{header[0:4]}")
        if header[4:5] != b'\x02':
            raise storepass.exc.StorageReadException(
                f"Unsupported data version, expected b'2' but found "
                f"{header[4:5]}")
        if header[5:6] != b'\x00':
            raise storepass.exc.StorageReadException(
                f"Non-zero header padding at bytes [5:6), found {header[5:6]}")
        # Ignore app version at header[6:9].
        if header[9:] != b'\x00\x00\x00':
            raise storepass.exc.StorageReadException(
                f"Non-zero header padding at bytes [9:12), found {header[9:]}")

    def read_plain(self, raw_bytes=False):
        """
        Read and decrypt the password database. Return its plain XML content.

        If raw_bytes is True, a bytes object is returned, otherwise the data is
        decoded as UTF-8 and a Unicode string returned.
        """

        try:
            with open(self._filename, 'rb') as fh:
                raw_content = fh.read()
        except Exception as e:
            raise storepass.exc.StorageReadException(e) from e

        # Split the content.
        if len(raw_content) < 12:
            raise storepass.exc.StorageReadException(
                f"File header is incomplete, expected '12' bytes but found "
                f"'{len(raw_content)}'")
        header = raw_content[:12]
        if len(raw_content) < 20:
            raise storepass.exc.StorageReadException(
                f"Salt record is incomplete, expected '8' bytes but found "
                f"'{len(raw_content)-12}'")
        salt = raw_content[12:20]
        if len(raw_content) < 36:
            raise storepass.exc.StorageReadException(
                f"Initialization vector is incomplete, expected '16' bytes but "
                f"found '{len(raw_content)-20}'")
        init_vector = raw_content[20:36]

        encrypted_data = raw_content[36:]
        if len(encrypted_data) % 16 != 0:
            raise storepass.exc.StorageReadException(
                f"Data record with size of '{len(encrypted_data)}' bytes is "
                f"not 16-byte aligned")

        # Parse and validate the header.
        self._parse_header(header)

        # Calculate the PBKDF2 derived key.
        password = self.get_password()
        key = hashlib.pbkdf2_hmac('sha1', password.encode('utf-8'), salt, 12000,
                                  dklen=32)

        # Decrypt the data.
        crypto_obj = AES.new(key, AES.MODE_CBC, init_vector)
        decrypted_data = crypto_obj.decrypt(encrypted_data)

        hash256 = decrypted_data[0:32]
        compressed_data = decrypted_data[32:]

        if len(compressed_data) == 0:
            raise storepass.exc.StorageReadException(
                "Compressed data have zero size")

        # Verify the hash of decrypted data.
        if hashlib.sha256(compressed_data).digest() != hash256:
            raise storepass.exc.StorageReadException("Incorrect password")

        # Decompress the data.
        padlen = compressed_data[-1]
        if padlen > 15:
            raise storepass.exc.StorageReadException(
                f"Compressed data have incorrect padding, length '{padlen}' is "
                f"bigger than '15' bytes")
        actual_padding = compressed_data[-padlen:]
        expected_padding = padlen * padlen.to_bytes(1, 'little')
        if actual_padding != expected_padding:
            raise storepass.exc.StorageReadException(
                f"Compressed data have incorrect padding, expected "
                f"{expected_padding} but found {actual_padding}")

        try:
            decompressed_data = zlib.decompress(compressed_data[0:-padlen])
        except Exception as e:
            raise storepass.exc.StorageReadException(e) from e

        # Return the raw bytes if requested.
        if raw_bytes:
            return decompressed_data

        # Decode the data as UTF-8.
        try:
            return decompressed_data.decode('utf-8')
        except Exception as e:
            raise storepass.exc.StorageReadException(
                f"Error decoding payload: {e}") from e

    def read_tree(self):
        """
        Read and decrypt the password database. Return its normalized tree
        structure.
        """

        # Read and decrypt the file. Request the data to be returned as bytes so
        # ElementTree can handle decoding according to the XML specification.
        xml_data = self.read_plain(raw_bytes=False)

        xml_to_model = _XMLToModelConvertor()
        return xml_to_model.process(xml_data)

    def write_plain(self, xml):
        """
        Encrypt plain XML content and save it into the password database.
        """

        # Encode the Unicode data as UTF-8.
        encoded_data = xml.encode('utf-8')

        # Compress the data.
        try:
            compressed_unpadded_data = zlib.compress(encoded_data)
        except Exception as e:
            raise storepass.exc.StorageWriteException(e) from e

        # Pad the result to the 16-byte boundary.
        padlen = 16 - len(compressed_unpadded_data) % 16
        compressed_data = compressed_unpadded_data + bytes([padlen] * padlen)

        # Add a hash for integrity check.
        hash256 = hashlib.sha256(compressed_data).digest()
        decrypted_data = hash256 + compressed_data

        # Calculate the PBKDF2 derived key.
        password = self.get_password()
        salt = os.urandom(8)
        key = hashlib.pbkdf2_hmac('sha1', password.encode('utf-8'), salt, 12000,
                                  dklen=32)

        # Encrypt the data.
        init_vector = os.urandom(16)
        crypto_obj = AES.new(key, AES.MODE_CBC, init_vector)
        encrypted_data = crypto_obj.encrypt(decrypted_data)

        # Prepare final output and write it out.
        raw_content = b'rvl\x00\x02\x00\x00\x00\x00\x00\x00\x00' + \
            salt + init_vector + encrypted_data

        try:
            with open(self._filename, 'wb') as fh:
                fh.write(raw_content)
        except Exception as e:
            raise storepass.exc.StorageWriteException(e) from e

    def write_tree(self, root):
        """
        Convert a password tree structure into a XML representation, encrypt it
        and save into the password database.
        """

        model_to_xml = _ModelToXMLConvertor()
        xml_data = model_to_xml.process(root)
        self.write_plain(xml_data)
