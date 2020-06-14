# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import Crypto.Cipher.AES
import datetime
import hashlib
import itertools
import os
import xml.etree.ElementTree as ET
import zlib

import storepass.exc
import storepass.model


class _XMLToModelConvertor:
    """XML to internal data model convertor."""
    def __init__(self):
        # Pass as the convertor is stateless.
        pass

    class _EntryProperties:
        """
        Aggregate to hold common entry properties.
        """
        def __init__(self):
            self.name = None
            self.description = None
            self.updated = None
            self.notes = None

    class _XPath(list):
        """
        A list sub-class to track an XPath to XML elements in the processed
        database.
        """
        def __str__(self):
            return ''.join(self)

        def push(self, item):
            """Append a new element to the end of the path."""
            self.append(item)

    def process(self, xml_data):
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

    def _parse_entry_property(self, xml_elem, xpath, props):
        """
        Parse a common property element <name>, <description>, <updated> or
        <notes>.
        """

        self._validate_element_attributes(xml_elem, xpath, ())

        if xml_elem.tag == 'name':
            props.name = xml_elem.text
        elif xml_elem.tag == 'description':
            props.description = xml_elem.text
        elif xml_elem.tag == 'updated':
            props.updated = self._parse_updated(xml_elem, xpath)
        else:
            assert xml_elem.tag == 'notes'
            props.notes = xml_elem.text

    def _parse_subentries(self, xml_elem, xpath, xml_elem_iter):
        """Parse sub-entries of a folder-like element."""

        children = []
        path_i = 1
        for xml_elem in xml_elem_iter:
            if xml_elem.tag != 'entry':
                raise storepass.exc.StorageReadException(
                    f"Unrecognized element '{xpath}/{xml_elem.tag}', expected "
                    f"'entry'")

            xpath.push(f'/entry[{path_i}]')
            path_i += 1

            self._validate_element_attributes(xml_elem, xpath, ('type'))

            type_ = xml_elem.get('type')
            if type_ == 'folder':
                folder = self._parse_folder(xml_elem, xpath)
                children.append(folder)
            elif type_ == 'generic':
                generic = self._parse_generic(xml_elem, xpath)
                children.append(generic)
            else:
                raise storepass.exc.StorageReadException(
                    f"Attribute '{xpath}/@type' has unrecognized value "
                    f"'{type_}', expected 'folder' or 'generic'")

            xpath.pop()

        return children

    def _parse_folder(self, xml_elem, xpath):
        """Parse a <entry type='folder'> element."""

        assert xml_elem.tag == 'entry'
        assert xml_elem.get('type') == 'folder'

        props = self._EntryProperties()
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
                self._parse_entry_property(xml_subelem, xpath, props)
            else:
                raise storepass.exc.StorageReadException(
                    f"Unrecognized sub-folder element '{xpath}'")

            xpath.pop()

        children = self._parse_subentries(xml_elem, xpath, xml_subelem_iter)

        return storepass.model.Folder(props.name, props.description,
                                      props.updated, props.notes, children)

    def _parse_generic(self, xml_elem, xpath):
        """Parse a <entry type='generic'> element."""

        assert xml_elem.tag == 'entry'
        assert xml_elem.get('type') == 'generic'

        props = self._EntryProperties()
        username = None
        password = None
        hostname = None

        for xml_subelem in list(xml_elem):
            xpath.push(f'/{xml_subelem.tag}')

            if xml_subelem.tag in ('name', 'description', 'updated', 'notes'):
                self._parse_entry_property(xml_subelem, xpath, props)
            elif xml_subelem.tag == 'field':
                self._validate_element_attributes(xml_subelem, xpath, ('id'))

                id_ = xml_subelem.get('id')
                if id_ == 'generic-hostname':
                    hostname = xml_subelem.text
                elif id_ == 'generic-username':
                    username = xml_subelem.text
                elif id_ == 'generic-password':
                    password = xml_subelem.text
                else:
                    raise storepass.exc.StorageReadException(
                        f"Attribute '{xpath}/@id' has unrecognized value "
                        f"'{id_}', expected 'generic-hostname', "
                        f"'generic-username' or 'generic-password'")
            else:
                raise storepass.exc.StorageReadException(
                    f"Unrecognized sub-generic element '{xpath}'")

            xpath.pop()

        return storepass.model.Generic(props.name, props.description,
                                       props.updated, props.notes, hostname,
                                       username, password)


class _ModelToXMLConvertor(storepass.model.ModelVisitor):
    """Internal data model to XML convertor."""
    def __init__(self):
        super().__init__()

        self._xml_root = None

    def _indent_xml(self, xml_element, level=0):
        """Indent elements of a given ElementTree for pretty-print."""

        indent = '\n' + '\t' * level
        if len(xml_element) > 0:
            xml_element.text = indent + '\t'
            for xml_subelement in xml_element:
                self._indent_xml(xml_subelement, level + 1)
            xml_subelement.tail = indent
        xml_element.tail = indent

    def process(self, root):
        """
        Process a password tree structure and return its XML representation (as
        a string).
        """

        self._xml_root = None
        assert len(self._path) == 0

        # Visit all nodes and create their ElementTree representation.
        root.accept(self)

        # Convert ElementTree representation to a XML document.
        self._indent_xml(self._xml_root)
        return ET.tostring(self._xml_root,
                           encoding='unicode',
                           xml_declaration=True)

    def visit_root(self, root):
        """Create XML representation for the data root."""

        self._xml_root = ET.Element('revelationdata')
        self._xml_root.set('dataversion', '1')

        return self._xml_root

    def _add_entry_properties(self, entry, xml_entry):
        """Create XML representation for common password entry properties."""

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

    def visit_folder(self, folder):
        """Create XML representation for a password folder."""

        xml_parent = self.get_path_data(folder.parent)

        xml_folder = ET.SubElement(xml_parent, 'entry')
        xml_folder.set('type', 'folder')
        self._add_entry_properties(folder, xml_folder)

        return xml_folder

    def visit_generic(self, generic):
        """Create XML representation for a generic password record."""

        xml_parent = self.get_path_data(generic.parent)

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

        return xml_generic


class Storage:
    """Password database file reader/writer."""
    def __init__(self, filename, password):
        self.filename = filename
        self.password = password

    def _get_real_password(self):
        if callable(self.password):
            return self.password()
        else:
            return self.password

    def _parse_header(self, header):
        """Verify validity of a password database header."""

        assert len(header) == 12

        if header[:4] != b'rvl\x00':
            raise storepass.exc.StorageReadException(
                f"Invalid magic number, expected b'rvl\\x00' but found "
                f"{header[0:4]}")
        if header[4:5] != b'\x02':
            raise storepass.exc.StorageReadException(
                f"Unsupported envelope data version, expected b'2' but found "
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
                f"Compressed data have incorrect padding, length '{padlen}' is "
                f"bigger than '16' bytes")
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

    def write_plain(self, xml, exclusive=False):
        """
        Encrypt plain XML content and save it into the password database. If
        exclusive is True then it is checked during opening of the file that it
        does not exist yet.
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
        raw_content = b'rvl\x00\x02\x00\x00\x00\x00\x00\x00\x00' + \
            salt + init_vector + encrypted_data

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
        Convert a password tree structure into a XML representation, encrypt it
        and save into the password database. The exclusive argument has the same
        meaning as in the method write_plain().
        """

        model_to_xml = _ModelToXMLConvertor()
        xml_data = model_to_xml.process(root)
        self.write_plain(xml_data, exclusive)
