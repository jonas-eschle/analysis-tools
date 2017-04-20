#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   setup.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   16.02.2017
# =============================================================================
"""Generic analysis package."""

from setuptools import setup
setup(name='analysis',
      version='1.0',
      description='Generic analysis package',
      url='https://gitlab.cern.ch/apuignav/analysis-tools/',
      author='Albert Puig',
      author_email='albert.puig@cern.ch',
      license='BSD3',
      install_requires=['tables',
                        'h5py',
                        'pandas',
                        'colorlog',
                        'fasteners',
                        'PyYAML',
                        'contextlib2',
                        'yamlordereddictloader',
                        'git+git://github.com/ibab/root_pandas.git'],
      packages=['analysis'],
      zip_safe=False)

# EOF
