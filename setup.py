#!/usr/bin/env python
from setuptools import setup

setup(name='hardlinkpy',
      version='0.5',
      description='Filesystem deduplification',
      author='John Villalovos',
      author_email='john@sodarock.com',
      py_modules=["hardlink"],
      test_suite="tests",
      entry_points={
          'console_scripts': ['hardlink=hardlink.main']
      })
