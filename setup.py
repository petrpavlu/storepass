# Copyright (C) 2019 Petr Pavlu <setup@dagobah.cz>
# SPDX-License-Identifier: MIT

import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='storepass',
    version='0.1',
    author='Petr Pavlu',
    author_email='petr.pavlu@outlook.com',
    description='StorePass Password Manager',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/petrpavlu/storepass',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'storepass = storepass.cli.__main__:main',
        ],
    },
    packages=setuptools.find_packages(),
)
