#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   data.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   16.01.2017
# =============================================================================
"""Fit-related utils."""
from __future__ import print_function, division, absolute_import

import pandas as pd

from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.utils.fit')


def fit_parameters_to_dict(parameters):
    """Extract the important information of fit parameters.

    This allows to store uncertainties in pandas dataframes.

    For each parameter `par` in `parameters` the following entries are stored:
        - `{par}`: value.
        - `{par}_err_hesse`: parabolic error (`getError` method).
        - `{par}_err_plus`: upper error (`getErrorHi`).
        - `{par}_err_minus`: signed lower error (`getErrorLo`).

    Arguments:
        parameters (list[`ROOT.RooRealVar`]): Fit parameters

    Return:
        dict.

    """
    return {(param.GetName() + suffix): getattr(param, method)()
            for param in parameters
            for method, suffix in (('getValV', ''),
                                   ('getError', '_err_hesse'),
                                   ('getErrorHi', '_err_plus'),
                                   ('getErrorLo', '_err_minus'))
            if hasattr(param, method)}


def calculate_pulls(fit_results, gen_values):
    """Calculate pulls.

    For each parameter `par`, the following information is obtained:
        - `{par}_pull_diff`: fit - gen.
        - `{par}_pull_hesse`: pull calculated with the Hesse error.
        - `{par}_pull_minos`: pull calculated with the asymmetric Minos errors.

    Arguments:
        fit_results (`pandas.DataFrame`): Frame containing fit values and errors.
        gen_values (`pandas.DataFrame`): Frame containing generator values.

    Return:
        pandas.DataFrame: Data frame containing pull information for all
            fitted parameters.

    """
    pulls = pd.DataFrame()
    for param_name in fit_results.columns:
        # Horrible, need to improve this
        if any((param_name == 'fit_status',
                param_name.endswith('_err_hesse'),
                param_name.endswith('_err_plus'),
                param_name.endswith('_err_minus'))):
            continue
        # Calculate pulls only for matching parameters
        gen_name = param_name + '_{gen}'
        if gen_name not in gen_values.columns:
            continue
        pulls[param_name + '_pull_diff'] = fit_results[param_name] - gen_values[gen_name]
        pulls[param_name + '_pull_hesse'] = pulls[param_name + '_pull_diff'] / fit_results[param_name + '_err_hesse']
        pulls[param_name + '_pull_minos'] = pulls[param_name + '_pull_diff'] / \
                                            fit_results[param_name + '_err_plus']
        pulls[param_name + '_pull_minos'][pulls[param_name + '_pull_diff'] > 0.0] = pulls[param_name + '_pull_diff'] / \
                                                                                    fit_results[
                                                                                        param_name + '_err_minus'].abs()
    return pulls

# EOF
