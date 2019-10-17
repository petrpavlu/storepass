# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import hashlib
import xml.etree.ElementTree as ET
import zlib

from Crypto.Cipher import AES

class ReadException(Exception):
    pass

class StorageProxy:
    TYPE_ROOT = 0
    TYPE_FOLDER = 1
    TYPE_GENERIC = 2

    def __init__(self, type_, attrs, children):
        self._type = type_
        self._attrs = attrs
        self._children = children

    @property
    def type(self):
        return self._type

    @property
    def attributes(self):
        return self._attrs

    @property
    def children(self):
        return self._children

class Storage:
    """Password database file reader/writer."""

    def __init__(self, filename, password_proxy):
        self._filename = filename
        self._password_proxy = password_proxy

    def read_plain(self):
        """
        Read and decode the password database. Return its plain XML content.
        """

        try:
            fi = open(self._filename, 'rb')
        except Exception as e:
            raise ReadException(e) from e
        else:
            with fi:
                raw_content = fi.read()
                return self._decode_raw_content(raw_content)

    def _decode_raw_content(self, raw_content):
        """Decode a password database content."""

        # Split the content.
        if len(raw_content) < 12:
            raise ReadException("File header is incomplete")
        header = raw_content[:12]
        if len(raw_content) < 20:
            raise ReadException("Salt record is incomplete")
        salt = raw_content[12:20]
        if len(raw_content) < 36:
            raise ReadException("Initialization vector is incomplete")
        init_vector = raw_content[20:36]

        encrypted_data = raw_content[36:]
        if len(encrypted_data) % 16 != 0:
            raise ReadException(
                "Size of the data record is not 16-byte aligned")

        # Parse and validate the header.
        self._parse_header(header)

        # Query the password for the file.
        if callable(self._password_proxy):
            password = self._password_proxy()
        else:
            password = self._password_proxy

        # Calculate the PBKDF2 derived key.
        key = hashlib.pbkdf2_hmac('sha1', password.encode('utf-8'), salt, 12000,
                                  dklen=32)

        # Decrypt the data.
        crypto_obj = AES.new(key, AES.MODE_CBC, init_vector)
        decrypted_data = crypto_obj.decrypt(encrypted_data)

        # TODO Check the size is big enough?
        hash256 = decrypted_data[0:32]
        compressed_data = decrypted_data[32:]

        # Verify the hash of decrypted data.
        if hashlib.sha256(compressed_data).digest() != hash256:
            raise ReadException("Incorrect password")

        # Decompress the data.
        padlen = compressed_data[-1]
        # TODO Check bounds?
        if compressed_data[-padlen:] != padlen * padlen.to_bytes(1, 'little'):
            raise ReadException("Decompressed data have incorrect padding")

        # TODO Check for errors.
        decompressed_data = zlib.decompress(compressed_data[0:-padlen])

        # TODO Check for errors.
        return decompressed_data.decode('utf-8')

    def _parse_header(self, header):
        """Verify validity of a password database header."""

        assert len(header) == 12

        if header[:4] != b'rvl\x00':
            raise ReadException("Invalid magic number")
        if header[4:5] != b'\x02':
            raise ReadException("Unsupported data version '{}'".format(
                header[4]))
        if header[5:6] != b'\x00':
            raise ReadException("Non-zero header padding at bytes [5:6)")
        # Ignore app version at header[6:9].
        if header[9:] != b'\x00\x00\x00':
            raise ReadException("Non-zero header padding at bytes [9:12)")

    def read_tree(self):
        """
        Read and decode the password database. Return its normalized tree
        structure.
        """

        xml_data = self.read_plain()

        # TODO Implement proper error checking.
        root_elem = ET.fromstring(xml_data)

        return self._parse_root(root_elem)

    def _parse_root(self, xml_elem):
        """Parse the root <revelationdata> element."""

        if xml_elem.tag != 'revelationdata':
            raise ReadException(
                f"Invalid root element '{xml_elem.tag}', expected " \
                f"'revelationdata'")

        # TODO Validate that the element has no unrecognized attributes.

        children = self._parse_subelements(iter(list(xml_elem)))
        return StorageProxy(StorageProxy.TYPE_ROOT, [], children)

    def _parse_subelements(self, xml_elem_iter):
        """Parse sub-elements of a folder-like element."""

        children = []
        for xml_elem in xml_elem_iter:
            if xml_elem.tag != 'entry':
                raise ReadException(
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
                raise ReadException(
                    f"Unrecognized type attribute '{type_}', expected 'folder' or 'generic'")

        return children

    def _parse_folder(self, xml_elem):
        """Parse a <entry type='folder'> element."""

        assert xml_elem.tag == 'entry'
        assert xml_elem.get('type') == 'folder'

        xml_subelem_iter = iter(list(xml_elem))

        attrs = []
        for xml_subelem in xml_subelem_iter:
            if xml_subelem.tag == 'entry':
                break

            # TODO Improve the parsing and checking.
            attrs.append((xml_subelem.tag, xml_subelem.text))

        children = self._parse_subelements(xml_subelem_iter)

        return StorageProxy(StorageProxy.TYPE_FOLDER, attrs, children)

    def _parse_generic(self, xml_elem):
        """Parse a <entry type='generic'> element."""

        assert xml_elem.tag == 'entry'
        assert xml_elem.get('type') == 'generic'

        attrs = []
        for xml_subelem in list(xml_elem):
            attrs.append((xml_subelem.tag, xml_subelem.text))

        return StorageProxy(StorageProxy.TYPE_GENERIC, attrs, [])
