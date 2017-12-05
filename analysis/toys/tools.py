#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   tools.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   14.03.2017
# =============================================================================
"""Common tools for managing toys."""
from __future__ import print_function, division, absolute_import

import os
import contextlib2

import pandas as pd

from analysis.utils.paths import get_toy_fit_path
from analysis.utils.logging_color import get_logger

_logger = get_logger('analysis.toys.tools')


def load_toy_fits(*toys, **kwargs):
    """Load toy fit results.

    If several files are given, all the tables are merged.

    Note:
        The HDFStores are opened and closed. A copy of the data frames
        is returned.

    Arguments:
        *toys (str): Toy names to load.
        **kwargs (dict): Extra options:
            + `index` (bool, optional): Index the data frame? Defaults
            to `True`.
            + `fail_on_incompatible` (bool, optional): Fail when incompatible
            data frames are found? Defaults to `True`.

    Return:
        `pandas.DataFrame`: Merged data frame.

    Raise:
        OSError: If some of the toys do not exist.
        KeyError: If the data frames from the different stores are not compatible
            and `fail_on_incompatible` is set.

    """
    # Check that toys exist
    if not all(os.path.exists(get_toy_fit_path(toy_name)) for toy_name in toys):
        raise OSError("Cannot load all toys")
    with contextlib2.ExitStack() as toy_stack:
        # toy_results = []
        fit_cov_matrices = []
        fit_results = []
        for toy_name in toys:
            toy_result = toy_stack.enter_context(pd.HDFStore(get_toy_fit_path(toy_name), mode='r'))
            fit_result = toy_result['fit_results']
            fit_results.append(fit_result)
            cov_matrices = []
            for row in fit_result.iterrows():
                cov_path = os.path.join('covariance', row[1]['jobid'], row[1]['fit_num'])
                cov_matrices.append(toy_result[cov_path])
            fit_cov_matrices.append(cov_matrices)
        if not all(all(fit_result.columns == fit_results[0].columns)
                   for fit_result in fit_results):
            if kwargs.get('fail_on_incompatible', True):
                raise KeyError("Incompatible toy fits!")
            else:
                _logger.warning('Found incompatible data frames')
        merged_result = pd.concat(fit_results)
    if kwargs.get('index', True):
        indices = [col for col in merged_result.columns
                   if any((col in ['model_name', 'fit_strategy'],
                           '_{gen}' in col and not col.startswith('N^'),
                           '_{nominal}' in col))]
        merged_result.set_index(indices, inplace=True)
    return merged_result, fit_cov_matrices

# EOF
