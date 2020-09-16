# StorePass Password Manager

## Overview

StorePass a simple password manager with a command-line and graphical interface.
It is written in [Python 3][Python] and has its GUI built with [the GTK 3
toolkit][GTK]. The program uses the [Revelation][Revelation] data version 2 as
its storage format.

## Features

* Management of password entries via a command-line and graphical (GTK-based)
  interface.
* Encryption of user data with AES-256 and the key derived from a password
  using PBKDF2 (with 12000 iterations).
* Storage of all information in a single file, which allows for easy
  synchronization and makes private also a tree structure and names of the
  entries.
* Compatibility with the Revelation password manager.
* Written in Python 3, minimal dependencies, MIT license.

## Screenshots

| Main window | Edit dialog |
| :---------: | :---------: |
| ![Main window](https://user-images.githubusercontent.com/31453820/93376537-0c941d80-f85a-11ea-97ac-e8bb0b6d78b3.png) | ![Edit dialog](https://user-images.githubusercontent.com/31453820/93378202-64cc1f00-f85c-11ea-9d49-906d9aec4ce7.png) |

## Installation

StorePass uses Setuptools for its packaging and distribution, as is standard for
Python projects. The following steps can be used for installation from a release
tarball:

```
$ tar -xvzf storepass-<version>.tar.gz
$ cd storepass-<version>
$ python3 setup.py install --prefix=<install-location>
```

When working with a Git repository, it is possible to run the program directly
without installing it by invoking either `storepass-cli.py` or
`storepass-gtk.py`.

The following dependencies are required to run the program:
* [Python][Python] >= 3.8,
* [PyCryptodome][PyCryptodome],
* [GTK 3][GTK] for the graphical interface.

## Compatibility

StorePass uses the Revelation data version 2 as its storage format. The program
is therefore compatible with the Revelation password manager and other tools
that use the same format.

The use of this format is because StorePass was originally created as a simpler
replacement for Revelation which at that time looked long unmaintained.

## License

This project is released under the terms of [the MIT License](COPYING).

[Python]: https://www.python.org/
[GTK]: https://www.gtk.org/
[Revelation]: https://revelation.olasagasti.info/
[PyCryptodome]: https://pycryptodome.readthedocs.io/en/latest/
