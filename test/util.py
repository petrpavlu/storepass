# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Test helper functions."""

import hashlib
import os
import os.path
import shutil
import tempfile
import textwrap
import unittest
import zlib

import Crypto.Cipher.AES


class StorePassTestCase(unittest.TestCase):
    def setUp(self):
        self.testdir = tempfile.mkdtemp()

        # Set the default database name.
        self.dbname = os.path.join(self.testdir, 'pass.db')

    def tearDown(self):
        shutil.rmtree(self.testdir)


def dedent(text):
    return textwrap.dedent(text)


def dedent2(text):
    """
    Remove any common leading whitespace + character '|' from every line in
    the given text.
    """

    output = ''
    lines = textwrap.dedent(text).splitlines(True)
    for line in lines:
        assert line[:1] == '|'
        output += line[1:]
    return output


def write_file(filename, bytes_):
    """Write raw content (bytes) into a specified file."""

    with open(filename, 'wb') as fh:
        fh.write(bytes_)


def write_password_db(filename, password, xml, compress=True):
    """Write a password database file."""

    # Encode the data if needed.
    if isinstance(xml, bytes):
        encoded_data = xml
    else:
        encoded_data = xml.encode('utf-8')

    # Compress the data if requested.
    if compress:
        compressed_unpadded_data = zlib.compress(encoded_data)

        # Pad the result to the 16-byte boundary.
        padlen = 16 - len(compressed_unpadded_data) % 16
        compressed_data = compressed_unpadded_data + bytes([padlen] * padlen)
    else:
        compressed_data = encoded_data

    # Add a hash for integrity check.
    hash256 = hashlib.sha256(compressed_data).digest()
    decrypted_data = hash256 + compressed_data

    # Calculate the PBKDF2 derived key.
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
    output_data = (b'rvl\x00\x02\x00\x00\x00\x00\x00\x00\x00' + salt +
                   init_vector + encrypted_data)
    write_file(filename, output_data)


def read_password_db(filename, password, test_case):
    """Read a password database file and verify its basic properties."""

    with open(filename, 'rb') as fh:
        raw_content = fh.read()

    # Split the content.
    test_case.assertGreaterEqual(len(raw_content), 36)
    header = raw_content[:12]
    salt = raw_content[12:20]
    init_vector = raw_content[20:36]
    encrypted_data = raw_content[36:]
    test_case.assertEqual(len(encrypted_data) % 16, 0)

    # Validate the header.
    test_case.assertEqual(header[0:4], b'rvl\x00')  # magic
    test_case.assertEqual(header[4:5], b'\x02')  # data version
    test_case.assertEqual(header[5:6], b'\x00')  # padding
    test_case.assertEqual(header[6:9], b'\x00\x00\x00')  # app version
    test_case.assertEqual(header[9:], b'\x00\x00\x00')  # padding

    # Calculate the PBKDF2 derived key.
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
    test_case.assertGreater(len(compressed_data), 0)

    # Verify the hash of decrypted data.
    test_case.assertEqual(hashlib.sha256(compressed_data).digest(), hash256)

    # Decompress the data.
    padlen = compressed_data[-1]
    test_case.assertLessEqual(padlen, 16)
    actual_padding = compressed_data[-padlen:]
    expected_padding = padlen * padlen.to_bytes(1, 'little')
    test_case.assertEqual(actual_padding, expected_padding)

    decompressed_data = zlib.decompress(compressed_data[0:-padlen])
    return decompressed_data.decode('utf-8')
