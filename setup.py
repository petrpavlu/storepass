# Copyright (C) 2019-2020 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

"""Build script for setuptools."""

import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='storepass',
    version='1.1.0',
    author='Petr Pavlu',
    author_email='setup@dagobah.cz',
    description='StorePass Password Manager',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/petrpavlu/storepass',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    # At least Python 3.8 is required because of use of
    # xml.etree.ElementTree.tostring(xml_declaration=True).
    python_requires='>=3.8',
    # PyCryptodome is required for Crypto.Cipher.AES. Extra GUI dependencies on
    # GTK and PyGObject are not stated because they are not available through
    # PyPI.
    install_requires=[
        'pycryptodome',
    ],
    entry_points={
        'console_scripts': [
            'storepass-cli = storepass.cli.__main__:main',
        ],
        'gui_scripts': [
            'storepass-gtk = storepass.gtk.__main__:main',
        ],
    },
    # Include all packages in the installation with the exception of tests
    # which get only shipped in the distribution package (via MANIFEST.in).
    packages=setuptools.find_packages(exclude=['tests']),
    package_data={'storepass.gtk.resources': ['*.ui']},
)
