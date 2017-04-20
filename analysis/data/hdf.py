#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   hdf.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.04.2017
# =============================================================================
"""Deal with HDF files."""

import os
import shutil
from contextlib import contextmanager

import pandas as pd

from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.data.hdf')


@contextmanager
def modify_hdf(file_name, compress=True):
    """Context manager to exclusively open an HDF file and write it to disk on close.

    Note:
        File is compressed on closing.

    Arguments:
        file_name (str): Final (desination) file name to write to.
        compress (bool, optional): Compress the file after closing? This is very
            useful when appending to an existing file. Defaults to `True`.

    Yields:
        `pandas.HDFStore`: Store to modify.

    """
    mode = 'a' if os.path.exists(file_name) else 'w'
    with pd.HDFStore(file_name, mode=mode, format='table') as data_file:
        yield data_file
    logger.debug('Compressing...')
    if compress:
        os.system("ptrepack --chunkshape=auto --propindexes --complevel=9 --complib=blosc "
                  "%s %s.out" % (file_name, file_name))
        shutil.move("%s.out" % file_name, file_name)


# EOF
