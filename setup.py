#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   setup.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   16.02.2017
# =============================================================================
"""Generic analysis package."""
from __future__ import print_function, division, absolute_import

import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md')) as f:
    readme = f.read()

setup(name='analysis',
      version='4.0',
      description='Generic analysis package',
      long_description=readme,
      classifiers=[
          'Development Status :: 3 - Alpha',
          # 'Development Status :: 4 - Beta',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Natural Language :: English',
          'Operating System :: MacOS',
          'Operating System :: Unix',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Topic :: Scientific/Engineering :: Physics',
          ],
      keywords='HEP physics analysis toy fit',
      url='https://gitlab.cern.ch/apuignav/analysis-tools/',
      author='Albert Puig, Jonas Eschle',
      author_email='albert.puig@cern.ch, jonas.eschle@cern.ch',
      maintainer='Albert Puig',
      maintainer_email='albert.puig@cern.ch',
      license='GPLv3',
      install_requires=['tables',
                        'pandas>=0.20.3',
                        'colorlog',
                        'fasteners',
                        'PyYAML',
                        'contextlib2',
                        'yamlloader>=0.5.1',
                        'root_pandas>=0.2.0',
                        'numpy>=1.13.1',
                        'scipy',
                        'psutil',
                        'matplotlib',
                        'seaborn',
                        'formulate'],
      packages=['analysis'],
      data_files=['LICENSE', 'README.md'],
      zip_safe=False)

# EOF
