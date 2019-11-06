# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import hashlib
import os
import zlib

from Crypto.Cipher import AES

def write_file(filename, bytes_):
    with open(filename, 'wb') as fh:
        fh.write(bytes_)

def write_password_db(filename, password, xml, compress=True):
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
    key = hashlib.pbkdf2_hmac('sha1', password.encode('utf-8'), salt, 12000,
                              dklen=32)

    # Encrypt the data.
    init_vector = os.urandom(16)
    crypto_obj = AES.new(key, AES.MODE_CBC, init_vector)
    encrypted_data = crypto_obj.encrypt(decrypted_data)

    # Prepare final output and write it out.
    output_data = b'rvl\x00\x02\x00\x00\x00\x00\x00\x00\x00' + \
        salt + init_vector + encrypted_data
    write_file(filename, output_data)
