#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   hdf.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.04.2017
# =============================================================================
"""Deal with HDF files."""
from __future__ import print_function, division, absolute_import

import os
import subprocess
import shutil
from contextlib import contextmanager

import pandas as pd

from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.data.hdf')


@contextmanager
def modify_hdf(file_name, compress=True):
    """Context manager to process-exclusively open an HDF file and write it to disk on close.

    Note:
        This does **NOT** work for threads! The lock applied is an inter-process lock
        and invokes the fcntl(2) system call.

    Note:
        File is compressed on closing. If compression fails, a warning is issued but
        no error is raised.

    Arguments:
        file_name (str): Final (destination) file name to write to.
        compress (bool, optional): Compress the file after closing? This is very
            useful when appending to an existing file. Defaults to `True`.

    Yields:
        `pandas.HDFStore`: Store to modify.

    """
    mode = 'w'
    if os.path.exists(file_name):
        with pd.HDFStore(file_name, mode='a', format='table') as test_len_file:
            if len(test_len_file) > 0:
                mode = 'a'
            else:
                logger.info("File %s exists but seems empty -> not construct with pytables?"
                            "Overwriting existing file!", file_name)
            test_len_file.flush(fsync=True)
    with pd.HDFStore(file_name, mode=mode, format='table') as data_file:
        yield data_file
        data_file.flush(fsync=True)
    logger.debug('Compressing...')
    if compress:
        compressed_file = "{}.out".format(file_name)
        try:
            cmd = ["ptrepack",
                   "--chunkshape=auto",
                   "--propindexes",
                   "--complevel=9",
                   "--complib=blosc",
                   file_name, compressed_file]
            out = subprocess.check_output(cmd)
            if not os.path.exists(compressed_file):  # Something went wrong
                raise subprocess.CalledProcessError(0, ' '.join(cmd), output=out)
        except subprocess.CalledProcessError as error:
            logger.warning("Error compressing -> %s", error.output)
        else:
            try:
                shutil.move(compressed_file, file_name)
            except IOError as error:
                logger.warning("Error moving (copying) compressed file -> %s", error)
        finally:
            if os.path.exists(compressed_file):
                os.remove(compressed_file)


# EOF
