# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""
Module to read/write a password database from/to a file.

This module provides functionality to read and write a password database file:
* The read operation takes an encrypted password database file, decrypts it,
  parses its XML content and produces an internal data model representing the
  data. Exception storepass.exc.StorageReadException is raised if an error
  occurs.
* The write operation takes an internal data model, prepares its XML
  representation and writes it encrypted into a file. Exception
  storepass.exc.StorageWriteException is raised if an error occurs.
"""

import datetime
import hashlib
import itertools
import os
import xml.etree.ElementTree as ET
import zlib

import Crypto.Cipher.AES

import storepass.exc
import storepass.model
import storepass.util

_STORAGE_ID_TO_ENTRY_TYPE_MAP = {
    cls.storage_id: cls
    for cls in storepass.model.ENTRY_TYPES
}


class _XMLToModelConvertor:
    """XML to internal data model convertor."""
    def __init__(self):
        """Initialize an XML to internal data model converter."""
        # Nothing to do since the convertor is stateless.

    class _EntryProperties:
        """Aggregate to hold common entry properties."""
        def __init__(self):
            self.name = None
            self.description = None
            self.updated = None
            self.notes = None

    class _XPath(list):
        """List-based XPath to record XML elements in a processed database."""
        def __str__(self):
            return ''.join(self)

        def push(self, item):
            """Append a new element to the end of the path."""
            self.append(item)

    def process(self, xml_data):
        """Parse a given XML document and return its data model."""
        try:
            root_elem = ET.fromstring(xml_data)
        except ET.ParseError as e:
            raise storepass.exc.StorageReadException(
                f"Error parsing XML payload: {e}") from e

        xpath = self._XPath()
        xpath.push(f'/{root_elem.tag}')
        res = self._parse_root(root_elem, xpath)
        assert len(xpath) == 1
        return res

    def _validate_element_attributes(self, xml_elem, xpath,
                                     accepted_attributes):
        """Check that the element has no unexpected attribute."""
        for attrib in xml_elem.attrib:
            if attrib not in accepted_attributes:
                raise storepass.exc.StorageReadException(
                    f"Element '{xpath}' has unrecognized attribute '{attrib}'")

    def _parse_root(self, xml_elem, xpath):
        """Parse the root <revelationdata> element."""
        if xml_elem.tag != 'revelationdata':
            raise storepass.exc.StorageReadException(
                f"Invalid root element '{xpath}', expected 'revelationdata'")

        # Note: The 'version' attribute is ignored.
        self._validate_element_attributes(xml_elem, xpath,
                                          ('version', 'dataversion'))

        dataversion = xml_elem.get('dataversion')
        if dataversion != '1':
            raise storepass.exc.StorageReadException(
                f"Unsupported XML data version, expected attribute "
                f"'{xpath}/@dataversion' to be '1' but found '{dataversion}'")

        children = self._parse_subentries(xml_elem, xpath,
                                          iter(list(xml_elem)))

        return storepass.model.Root(children)

    def _parse_updated(self, xml_elem, xpath):
        """Parse a <updated> element."""
        updated = xml_elem.text
        if updated is None:
            raise storepass.exc.StorageReadException(
                f"Element '{xpath}' has invalid value '': string is empty")
        if not updated.isdigit():
            raise storepass.exc.StorageReadException(
                f"Element '{xpath}' has invalid value '{updated}': string "
                f"contains a non-digit character")

        updated_int = int(updated)

        try:
            return datetime.datetime.fromtimestamp(updated_int,
                                                   datetime.timezone.utc)
        except (OverflowError, OSError) as e:
            raise storepass.exc.StorageReadException(
                f"Element '{xpath}' has invalid value '{updated}': {e}") from e

    def _parse_entry_property(self, xml_elem, xpath, entry_props):
        """
        Parse one of common property elements.

        Parse a common property element <name>, <description>, <updated> or
        <notes>.
        """
        self._validate_element_attributes(xml_elem, xpath, ())

        if xml_elem.tag == 'name':
            if xml_elem.text is None:
                raise storepass.exc.StorageReadException(
                    f"Element '{xpath}' has invalid value '': string is empty")
            entry_props.name = xml_elem.text
        elif xml_elem.tag == 'description':
            entry_props.description = xml_elem.text
        elif xml_elem.tag == 'updated':
            entry_props.updated = self._parse_updated(xml_elem, xpath)
        else:
            assert xml_elem.tag == 'notes'
            entry_props.notes = xml_elem.text

    def _parse_subentries(self, _xml_elem, xpath, xml_elem_iter):
        """Parse sub-entries of a folder-like element."""
        children = []
        path_i = 1
        for xml_subelem in xml_elem_iter:
            if xml_subelem.tag != 'entry':
                raise storepass.exc.StorageReadException(
                    f"Unrecognized element '{xpath}/{xml_subelem.tag}', "
                    f"expected 'entry'")

            xpath.push(f'/entry[{path_i}]')
            path_i += 1

            self._validate_element_attributes(xml_subelem, xpath, ('type'))

            type_ = xml_subelem.get('type')
            if type_ == storepass.model.Folder.storage_id:
                folder = self._parse_folder(xml_subelem, xpath)
                children.append(folder)
            elif type_ in _STORAGE_ID_TO_ENTRY_TYPE_MAP:
                account = self._parse_account(xml_subelem, xpath)
                children.append(account)
            else:
                accepted = ', '.join([
                    f"'{accepted_id}'"
                    for accepted_id in _STORAGE_ID_TO_ENTRY_TYPE_MAP.keys()
                ])
                raise storepass.exc.StorageReadException(
                    f"Attribute '{xpath}/@type' has unrecognized value "
                    f"'{type_}', expected one of: {accepted}")

            xpath.pop()

        return children

    def _validate_entry_name(self, _xml_elem, xpath, entry_name):
        """Validate an entry name."""
        if entry_name is None:
            raise storepass.exc.StorageReadException(
                f"Entry '{xpath}' has no name")

    def _parse_folder(self, xml_elem, xpath):
        """Parse a <entry type='folder'> element."""
        assert xml_elem.tag == 'entry'
        assert xml_elem.get('type') == storepass.model.Folder.storage_id

        entry_props = self._EntryProperties()
        xml_subelem_iter = iter(list(xml_elem))

        for xml_subelem in xml_subelem_iter:
            if xml_subelem.tag == 'entry':
                # Children entries reached. Add the peeked value back and bail
                # out.
                xml_subelem_iter = itertools.chain([xml_subelem],
                                                   xml_subelem_iter)
                break

            xpath.push(f'/{xml_subelem.tag}')

            if xml_subelem.tag in ('name', 'description', 'updated', 'notes'):
                self._parse_entry_property(xml_subelem, xpath, entry_props)
            else:
                raise storepass.exc.StorageReadException(
                    f"Unrecognized folder element '{xpath}'")

            xpath.pop()

        children = self._parse_subentries(xml_elem, xpath, xml_subelem_iter)

        self._validate_entry_name(xml_elem, xpath, entry_props.name)

        return storepass.model.Folder(entry_props.name,
                                      entry_props.description,
                                      entry_props.updated, entry_props.notes,
                                      children)

    def _parse_account(self, xml_elem, xpath):
        """Parse a <entry type='account-type'> element."""
        assert xml_elem.tag == 'entry'

        # Initialize entry and account-type property objects.
        entry_props = self._EntryProperties()
        account_props = {}
        type_ = xml_elem.get('type')
        type_cls = _STORAGE_ID_TO_ENTRY_TYPE_MAP[type_]
        valid_id_to_field_map = {
            field.storage_id: field
            for field in type_cls.entry_fields
        }

        # Process all sub-elements.
        field_i = 1
        for xml_subelem in list(xml_elem):
            xpath.push(f'/{xml_subelem.tag}')

            if xml_subelem.tag in ('name', 'description', 'updated', 'notes'):
                self._parse_entry_property(xml_subelem, xpath, entry_props)
            elif xml_subelem.tag == 'field':
                xpath.push(f'[{field_i}]')
                field_i += 1

                self._validate_element_attributes(xml_subelem, xpath, ('id'))

                id_ = xml_subelem.get('id')
                if id_ in valid_id_to_field_map:
                    field = valid_id_to_field_map[id_]
                    account_props[field] = xml_subelem.text
                else:
                    accepted = ', '.join([
                        f"'{accepted_id}'"
                        for accepted_id in valid_id_to_field_map.keys()
                    ])
                    raise storepass.exc.StorageReadException(
                        f"Attribute '{xpath}/@id' has unrecognized value "
                        f"'{id_}', expected one of: {accepted}")

                xpath.pop()
            else:
                raise storepass.exc.StorageReadException(
                    f"Unrecognized account element '{xpath}'")

            xpath.pop()

        self._validate_entry_name(xml_elem, xpath, entry_props.name)

        # Return the resulting account object.
        return type_cls.from_proxy(entry_props.name, entry_props.description,
                                   entry_props.updated, entry_props.notes,
                                   account_props)


class _ModelToXMLConvertor(storepass.model.ModelVisitor):
    """Internal data model to XML convertor."""
    def __init__(self):
        """Initialize an internal data model to XML converter."""
        super().__init__()
        self._xml_root = None

    def _indent_xml(self, xml_elem, level=0):
        """Indent elements of a given ElementTree for pretty-printing."""
        indent = '\n' + '\t' * level
        if len(xml_elem) > 0:
            xml_elem.text = indent + '\t'

            # Silence pylint to not report a warning about using a possibly
            # undefined loop variable.
            xml_subelem = None

            for xml_subelem in xml_elem:
                self._indent_xml(xml_subelem, level + 1)

            assert xml_subelem is not None
            xml_subelem.tail = indent

        xml_elem.tail = indent

    def process(self, root):
        """
        Process an internal data model and return its XML representation.

        Make a walk over a tree structure of an internal data model and return
        its complete XML representation as a string.
        """
        self._xml_root = None
        assert len(self._path) == 0

        # Visit all nodes and create their ElementTree representation.
        root.accept(self)

        # Convert ElementTree representation to an XML document.
        self._indent_xml(self._xml_root)
        return ET.tostring(self._xml_root,
                           encoding='unicode',
                           xml_declaration=True)

    def visit_root(self, _root):
        """Create XML representation for the data root."""
        self._xml_root = ET.Element('revelationdata')
        self._xml_root.set('dataversion', '1')
        return self._xml_root

    def visit_entry(self, entry):
        """Create XML representation for an entry."""
        xml_parent = self.get_path_data(entry.parent)
        xml_entry = ET.SubElement(xml_parent, 'entry')
        xml_entry.set('type', entry.storage_id)

        # Create XML representation for common entry properties.
        xml_name = ET.SubElement(xml_entry, 'name')
        xml_name.text = entry.name

        if entry.description is not None:
            xml_description = ET.SubElement(xml_entry, 'description')
            xml_description.text = entry.description

        if entry.updated is not None:
            xml_updated = ET.SubElement(xml_entry, 'updated')
            xml_updated.text = str(int(entry.updated.timestamp()))

        if entry.notes is not None:
            xml_notes = ET.SubElement(xml_entry, 'notes')
            xml_notes.text = entry.notes

        # Create XML representation for entry-specific properties.
        for field in entry.entry_fields:
            value = entry.properties[field]
            if value is not None:
                xml_field = ET.SubElement(xml_entry, 'field')
                xml_field.set('id', field.storage_id)
                xml_field.text = value

        return xml_entry


class Storage:
    """Password database file reader/writer."""
    def __init__(self, filename, password):
        """Initialize an XML to internal data model converter."""
        self.filename = filename
        self.password = password

    def _get_real_password(self):
        """Return a password to read/write the database."""
        if callable(self.password):
            return self.password()
        return self.password

    def _parse_header(self, header):
        """Verify validity of a password database header."""
        assert len(header) == 12
        if header[:4] != b'rvl\x00':
            raise storepass.exc.StorageReadException(
                f"Invalid magic number, expected b'rvl\\x00' but found "
                f"b'{storepass.util.escape_bytes(header[0:4])}'")
        if header[4:5] != b'\x02':
            raise storepass.exc.StorageReadException(
                f"Unsupported envelope data version, expected b'2' but found "
                f"b'{storepass.util.escape_bytes(header[4:5])}'")
        if header[5:6] != b'\x00':
            raise storepass.exc.StorageReadException(
                f"Non-zero header padding at bytes [5:6), found "
                f"b'{storepass.util.escape_bytes(header[5:6])}'")
        # Ignore app version at header[6:9].
        if header[9:] != b'\x00\x00\x00':
            raise storepass.exc.StorageReadException(
                f"Non-zero header padding at bytes [9:12), found "
                f"b'{storepass.util.escape_bytes(header[9:])}'")

    def read_plain(self, raw_bytes=False):
        """
        Read+decrypt a password database and return its plain content.

        Read password data from a configured file, decrypt it and return the
        plain XML content. If raw_bytes is True, a bytes object is returned,
        otherwise the data is decoded as UTF-8 and a Unicode string returned.
        """
        try:
            with open(self.filename, 'rb') as fh:
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
                f"Initialization vector is incomplete, expected '16' bytes "
                f"but found '{len(raw_content)-20}'")
        init_vector = raw_content[20:36]

        encrypted_data = raw_content[36:]
        if len(encrypted_data) % 16 != 0:
            raise storepass.exc.StorageReadException(
                f"Data record with size of '{len(encrypted_data)}' bytes is "
                f"not 16-byte aligned")

        # Parse and validate the header.
        self._parse_header(header)

        # Calculate the PBKDF2 derived key.
        password = self._get_real_password()
        key = hashlib.pbkdf2_hmac('sha1',
                                  password.encode('utf-8'),
                                  salt,
                                  12000,
                                  dklen=32)

        # Decrypt the data.
        crypto_obj = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_CBC,
                                           init_vector)
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
        if padlen > 16:
            raise storepass.exc.StorageReadException(
                f"Compressed data have incorrect padding, length '{padlen}' "
                f"is bigger than '16' bytes")
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
        Read+decrypt a password database and return its data model.

        Read password data from a configured file, decrypt it and return its
        data model.
        """
        # Read and decrypt the file. Request the data to be returned as bytes
        # so ElementTree can handle decoding according to the XML
        # specification.
        xml_data = self.read_plain(raw_bytes=False)

        xml_to_model = _XMLToModelConvertor()
        return xml_to_model.process(xml_data)

    def write_plain(self, xml, exclusive=False):
        """
        Store a plain XML content into an encrypted password database.

        Encrypt given XML data and write it into a configured file. If
        exclusive is True then a check is made during opening of the file that
        it does not exist yet.
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
        password = self._get_real_password()
        salt = os.urandom(8)
        key = hashlib.pbkdf2_hmac('sha1',
                                  password.encode('utf-8'),
                                  salt,
                                  12000,
                                  dklen=32)

        # Encrypt the data.
        init_vector = os.urandom(16)
        crypto_obj = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_CBC,
                                           init_vector)
        encrypted_data = crypto_obj.encrypt(decrypted_data)

        # Prepare final output and write it out.
        raw_content = (b'rvl\x00\x02\x00\x00\x00\x00\x00\x00\x00' + salt +
                       init_vector + encrypted_data)

        def open_for_writing(filename, exclusive):
            if exclusive:
                fd = os.open(filename, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    return os.fdopen(fd, 'wb')
                except:
                    # In case os.fdopen() fails, make sure that the file
                    # descriptor gets closed.
                    os.close(fd)
                    raise
            return open(filename, 'wb')

        try:
            with open_for_writing(self.filename, exclusive) as fh:
                fh.write(raw_content)
        except Exception as e:
            raise storepass.exc.StorageWriteException(e) from e

    def write_tree(self, root, exclusive=False):
        """
        Store a data model into an encrypted password database.

        Convert an internal data model to an XML document, encrypt it and write
        into a configured file. The exclusive argument has the same meaning as
        in the method write_plain()
        """
        model_to_xml = _ModelToXMLConvertor()
        xml_data = model_to_xml.process(root)
        self.write_plain(xml_data, exclusive)
