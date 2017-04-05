#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   data.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   16.01.2017
# =============================================================================
"""Pandas-related utils."""

import os
import shutil

from collections import defaultdict

from contextlib import contextmanager

import pandas as pd

import ROOT

import fasteners

from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.utils.data')


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


def pandas_from_dataset(dataset):
    """Create pandas DataFrame from a RooDataSet.

    Variable names are used as column names.

    Arguments:
        dataset (`ROOT.RooDataSet`): Dataset to convert to pandas.

    Returns:
        `pandas.DataFrame`

    """
    n_entries = dataset.numEntries()
    values = defaultdict(list)
    for i in range(n_entries):
        obs = dataset.get(i)
        obs_iter = obs.createIterator()
        var = obs_iter.Next()
        while var:
            values[var.GetName()].append(var.getVal())
            var = obs_iter.Next()
    return pd.DataFrame(values)


def dataset_from_pandas(frame, name, title, var_list=None, weight_var=None):
    """Build RooDataset from a Pandas DataFrame.

    Arguments:
        frame (pandas.DataFrame): DataFrame to convert.
        name (str): RooDataSet name.
        title (str): RooDataSet title.
        var_list (list[str], optional): List of variables to add to the dataset.
            If not given, all variables are converted.
        weight_var (str, optional): Assign the given variable name as weight.
            Defaults to None.

    Returns:
        ROOT.RooDataSet: Frame converted to dataset.

    Raises:
        KeyError: If the weight_var is not present in `frame`.

    """
    if weight_var and weight_var not in frame.columns:
        raise KeyError("Cannot find weight variable -> %s" % weight_var)
    var_names = var_list if var_list else list(frame.columns)
    dataset_vars = [ROOT.RooRealVar(var_name, var_name, 0.0)
                    for var_name in var_names]
    dataset_set = ROOT.RooArgSet()
    for var in dataset_vars:
        dataset_set.add(var)
    dataset = ROOT.RooDataSet(name, title, dataset_set)
    for _, row in frame.iterrows():
        for var_name in var_names:
            if isinstance(row[var_name], (float, int)):
                dataset_set.setRealValue(var_name, row[var_name])
        dataset.add(dataset_set)
    if weight_var:
        dataset = ROOT.RooDataSet(name, title, dataset_set,
                                  ROOT.RooFit.Import(dataset),
                                  ROOT.RooFit.WeightVar(weight_var))
    return dataset


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

    Returns:
        dict.

    """
    return {(param.GetName() + suffix): getattr(param, method)()
            for param in parameters
            for method, suffix in (('getValV', ''),
                                   ('getError', '_err_hesse'),
                                   ('getErrorHi', '_err_plus'),
                                   ('getErrorLo', '_err_minus'))}


def calculate_pulls(fit_results, gen_values):
    """Calculate pulls.

    For each parameter `par`, the following information is obtained:
        - `{par}_pull_diff`: fit - gen.
        - `{par}_pull_hesse`: pull calculated with the Hesse error.
        - `{par}_pull_minos`: pull calculated with the asymmetric Minos errors.

    Arguments:
        fit_results (`pandas.DataFrame`): Frame containing fit values and errors.
        gen_values (`pandas.DataFrame`): Frame containing generator values.

    Returns:
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
        gen_name = param_name +  '_{gen}'
        if gen_name not in gen_values.columns:
            continue
        pulls[param_name + '_pull_diff'] = fit_results[param_name] - gen_values[gen_name]
        pulls[param_name + '_pull_hesse'] = pulls[param_name + '_pull_diff'] / fit_results[param_name + '_err_hesse']
        pulls[param_name + '_pull_minos'] = pulls[param_name + '_pull_diff'] / \
            fit_results[param_name + '_err_plus']
        pulls[param_name + '_pull_minos'][pulls[param_name + '_pull_diff'] > 0.0] = pulls[param_name + '_pull_diff'] / \
            fit_results[param_name + '_err_minus'].abs()
    return pulls


# EOF
