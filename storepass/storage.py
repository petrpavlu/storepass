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

    def __init__(self, elem):
        if elem.tag == 'revelationdata' or elem.get('type') == 'folder':
            self._type = self.TYPE_FOLDER
        else:
            self._type = self.TYPE_GENERIC
        self._attrs = []
        self._children = []

        # Convert the XML element into a proxy.
        # TODO Validate the XML does not contain unrecognized values.
        for e in list(elem):
            if e.tag == 'entry':
                self._children.append(StorageProxy(e))
            else:
                self._attrs.append((e.tag, e.text))

    @property
    def type(self):
        return self._type

    @property
    def attributes(self):
        return self._attrs

    @property
    def children(self):
        return self._children

class Reader:
    def __init__(self, filename, password_proxy):
        self._root_elem = None

        # Read and decode the input file.
        try:
            fi = open(filename, 'rb')
        except Exception as e:
            raise ReadException(e) from e
        else:
            with fi:
                raw_content = fi.read()
                self._decode_raw_content(raw_content, password_proxy)

    def _decode_raw_content(self, raw_content, password_proxy):
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
        if callable(password_proxy):
            password = password_proxy()
        else:
            password = password_proxy

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

        data = zlib.decompress(compressed_data[0:-padlen])
        # TODO Remove.
        print(data.decode('utf-8'))

        # TODO Implement proper error checking.
        self._root_elem = ET.fromstring(data)

    def _parse_header(self, header):
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

    def get_root_node(self):
        return StorageProxy(self._root_elem)
