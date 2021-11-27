#!/usr/bin/env python
"""setup.py for the ntlib package"""

from distutils.core import setup
from os.path import dirname, join


def read(path):
    with open(join(dirname(__file__), path)) as fp:
        return fp.read()


setup(
    name='ntlib',
    version='0.1.0 alpha',
    description=('Library for processing Now Then archive files and some '
                 'other stuff'),
    long_description=read('README.md'),
    author='some rapid cow',
    author_email='thegent1ecow7513@gmail.com',
    packages=['ntlib'],
)
