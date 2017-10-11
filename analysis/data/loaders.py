#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   loaders.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.04.2017
# =============================================================================
"""Data loaders."""
from __future__ import print_function, division, absolute_import

import os
import random
import string

import ROOT

import numpy as np
import pandas as pd
from root_pandas import read_root

from analysis.data.converters import dataset_from_pandas
from analysis.utils.logging_color import get_logger
from analysis.utils.root import destruct_object, list_to_rooarglist


logger = get_logger('analysis.data.loaders')


###############################################################################
# Helpers
###############################################################################
def _analyze_weight_config(config):
    """Analyze weight config.

    Arguments:
        config (dict): `get_data` configuration.

    Returns:
        tuple (str, list, list): Name of the total weight variable, weight variables to
            normalize, weight variables not to normalize.

    Raises:
        KeyError: If there is some error in the configuration.
        ValueError: If there are common weights between to-normalize and not-to-normalize
            or if the name of the total weight variable corresponds to one of the weights.

    """
    # Check weights
    weights_to_normalize = config.get('weights-to-normalize', [])
    weights_not_to_normalize = config.get('weights-not-to-normalize', [])
    if set(weights_to_normalize) & set(weights_not_to_normalize):
        logger.error("Common weights between 'weights-to-normalize' and 'weights-not-to-normalize'")
        raise ValueError
    if not isinstance(weights_to_normalize, (list, tuple)):
        weights_to_normalize = [weights_to_normalize]
    if not isinstance(weights_not_to_normalize, (list, tuple)):
        weights_not_to_normalize = [weights_not_to_normalize]
    weights = weights_to_normalize + weights_not_to_normalize
    if weights :
        # If `weight-var-name` is specified, create a total weight variable with this name, otherwise create a total weight variable `totalWeight`
        weight_var = config.get('weight-var-name', 'totalWeight')
        # If `weight_var-name` corresponds to a weight, raise an error
        if set(weights_to_normalize + weights_not_to_normalize).intersection([weight_var]) :
            logger.error("'weight-var-name' is already used as weight")
            raise ValueError
    else :
        weight_var = None
    return weight_var, weights_to_normalize, weights_not_to_normalize


###############################################################################
# Load pandas files
###############################################################################
def _load_pandas(file_name, tree_name, variables, selection):
    """Load the pandas dataset.

    Arguments:
        file_name (str): File to load.
        tree_name (str): Tree to load.
        variables (list): List of variables to load (speeds up loading).
        selection (str): Not used right now.

    Returns:
        pandas.DataFrame

    Raises:
        OSError: If the input file does not exist.
        KeyError: If the tree is not found or some of the requested branches are missing.

    """
    if not os.path.exists(file_name):
        raise OSError("Cannot find input file -> {}".format(file_name))
    with pd.HDFStore(file_name, 'r') as store:
        if tree_name not in store:
            raise KeyError("Cannot find tree in input file -> {}".format(tree_name))
        if selection:
            output_data = store[tree_name].query(selection)
            if variables:
                output_data = output_data[variables]
        else:
            output_data = store.select(tree_name, columns=variables)
    return output_data


def get_pandas_from_pandas_file(file_name, tree_name, kwargs):
    """Load a pandas DataFrame from HDF file.

    Optional keys in `kwargs` are:
        + `variables`: List of variables to load.
        + `selection`: Selection to apply.

    Arguments:
        file_name (str): File to load.
        tree_name (str): Tree to load.
        **kwargs (dict): Extra configuration.

    """
    logger.debug("Loading pandas file in pandas format -> %s:%s",
                 file_name, tree_name)
    return _load_pandas(file_name, tree_name,
                        kwargs.get('variables', None),
                        kwargs.get('selection', None))


def get_root_from_pandas_file(file_name, tree_name, kwargs):
    """Load a pandas HDF file into a `ROOT.RooDataSet`.

    Needed keys in `kwargs` are:
        + `name`: Name of the `RooDataSet`.
        + `title`: Title of the `RooDataSet`.

    Optional keys are:
        + `variables`: List of variables to load.
        + `selection`: Selection to apply.
        + `weights-to-normalize`: Variables defining the weights that are normalized
            to the total number of entries of the dataset.
        + `weights-not-to-normalize`: Variables defining the weights that are not normalized.
        + `weight-var-name`: Name of the weight variable. If there is only one weight,
            it is not needed. Otherwise it has to be specified.
        + `acceptance`: Load an acceptance. This needs to be accompanied with a weight
            specification, either in `weights-to-normalize` or `weights-not-to-normalize`, which
            is either `acceptance_fit` or `acceptance_gen`. Depending on which one is
            specified, `acceptance.get_fit_weights` or `acceptance.get_gen_weights` is used.
        + `categories`: RooCategory variables to use.

    Arguments:
        file_name (str): File to load.
        tree_name (str): Tree to load.
        **kwargs (dict): Extra configuration.

    Returns:
        ROOT.RooDataSet: pandas.DataFrame converted to RooDataSet.

    Raises:
        KeyError: If there are errors in the `kwargs` variables.
        ValueError: If there is an error in loading the acceptance.

    """
    logger.debug("Loading pandas file in RooDataSet format -> %s:%s",
                 file_name, tree_name)
    # Checks and variable preparation
    try:
        name = kwargs['name']
        title = kwargs.get('title', name)
    except KeyError as error:
        raise KeyError("Missing configuration key -> {}".format(error))
    # Check weights
    try:
        weight_var, weights_to_normalize, weights_not_to_normalize = _analyze_weight_config(kwargs)
    except KeyError:
        raise KeyError("Badly specified weights")
    # Variables
    var_list = kwargs.get('variables', None)
    # Raise an error if some weights are not loaded.
    if not (set(weights_to_normalize+weights_not_to_normalize).issubset(set(var_list))) :
        raise ValueError("Missing weights in the list of variables read from input file.")
    acc_var = ''
    # Acceptance specified
    if 'acceptance' in kwargs:
        if any('acceptance_fit' in weights
               for weights in (weights_to_normalize, weights_not_to_normalize)):
            acc_var = 'acceptance_fit'
        if any('acceptance_gen' in weights
               for weights in (weights_to_normalize, weights_not_to_normalize)):
            if acc_var:
                raise ValueError("Specified both 'acceptance_fit' and 'acceptance_gen' as weights.")
            acc_var = 'acceptance_gen'
        if not acc_var:
            logger.warning("Requested acceptance but it has not been specified as a weight to use. Ignoring.")

    if weight_var:
        if 'acceptance' in kwargs:
            if any('acceptance_fit' in weights
                   for weights in (weights_to_normalize, weights_not_to_normalize)):
                acc_var = 'acceptance_fit'
            if any('acceptance_gen' in weights
                   for weights in (weights_to_normalize, weights_not_to_normalize)):
                if acc_var:
                    raise ValueError("Specified both 'acceptance_fit' and 'acceptance_gen' as weights.")
                acc_var = 'acceptance_gen'
            if not acc_var:
                logger.warning("Requested acceptance but it has not been specified as a weight to use. Ignoring.")
    # Load the data
    frame = _load_pandas(file_name, tree_name,
                         var_list,
                         kwargs.get('selection', None))
    if acc_var:
        from analysis.efficiency import get_acceptance
        try:
            acceptance = get_acceptance(kwargs['acceptance'])
        except Exception as error:
            raise ValueError(str(error))
        if acc_var in frame.columns:
            raise ValueError("Name clash: the column '{}' is present in the dataset".format(acc_var))
        if acc_var == 'acceptance_fit':
            frame['acceptance_fit'] = acceptance.get_fit_weights(frame)
        else:
            frame['acceptance_gen'] = acceptance.get_gen_weights(frame)
    # Apply weights
    if weight_var:
        frame[weight_var] = np.prod([frame[w_var] for w_var in weights_to_normalize],
                                    axis=0)
        frame[weight_var] = frame[weight_var]/frame[weight_var].sum()*frame.shape[0]
        frame[weight_var] = np.prod([frame[w_var] for w_var in weights_not_to_normalize + [weight_var]],
                                    axis=0)
    if var_list is not None and weight_var:
        var_list.append(weight_var)
    # Convert it
    return dataset_from_pandas(frame, name, title,
                               var_list=var_list,
                               weight_var=weight_var,
                               categories=kwargs.get('categories', None))


###############################################################################
# Load ROOT files
###############################################################################
def get_root_from_root_file(file_name, tree_name, kwargs):
    """Load a ROOT tree into a `ROOT.RooDataSet`.

    Needed keys in `kwargs` are:
        + `name`: Name of the `RooDataSet`.
        + `title`: Title of the `RooDataSet`.

    Optional keys are:
        + `variables`: List of variables to load.
        + `selection`: Selection to apply.

    Arguments:
        file_name (str): File to load.
        tree_name (str): Tree to load.
        **kwargs (dict): Extra configuration.

    Returns:
        ROOT.RooDataSet: ROOT file converted to RooDataSet.

    Raises:
        KeyError: If there are missing variables in `kwargs`.
        ValueError: If the requested variables cannot be found in the input file.

    """
    def get_list_of_leaves(tree):
        """Get list of leave names from a tree matching a certain regex.

        Arguments:
            tree (`ROOT.TTree`): Tree to extract the leaves from.

        Returns:
            list: Leaves of the tree.

        """
        object_list = tree.GetListOfLeaves()
        return [object_list[leave_number].GetName()
                for leave_number in range(object_list.GetSize())]

    logger.debug("Loading ROOT file in RooDataSet format -> %s:%s",
                 file_name, tree_name)
    if not os.path.exists(file_name):
        raise OSError("Cannot find input file -> {}".format(file_name))
    try:
        name = kwargs['name']
        title = kwargs.get('title', name)
    except KeyError as error:
        raise KeyError("Missing configuration key -> {}".format(error))
    tfile = ROOT.TFile.Open(file_name)
    tree = tfile.Get(tree_name)
    if not tree:
        raise KeyError("Cannot find tree in input file -> {}".format(tree_name))
    leaves = set(get_list_of_leaves(tree))
    variables = set(kwargs.get('variables', leaves))
    # Acceptance
    if 'acceptance' in kwargs:
        raise NotImplementedError("Acceptance weights are not implemented for ROOT files")
    # Check weights
    try:
        weight_var, weights_to_normalize, weights_not_to_normalize = _analyze_weight_config(kwargs)
    except KeyError:
        raise KeyError("Badly specified weights")
    if variables and weight_var:
        variables = set(variables) | set(weights_to_normalize) | set(weights_not_to_normalize)
    # Crosscheck leaves
    if variables - leaves:
        raise ValueError("Cannot find leaves in input -> {}".format(variables - leaves))
    selection = kwargs.get('selection', None)
    leave_set = ROOT.RooArgSet()
    leave_list = []
    if selection:
        for var in leaves:
            leave_list.append(ROOT.RooRealVar(var, var, 0.0))
            leave_set.add(leave_list[-1])
        name = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits)
                       for _ in range(10))
        temp_ds = ROOT.RooDataSet(name, name,
                                  leave_set,
                                  ROOT.RooFit.Import(tree),
                                  ROOT.RooFit.Cut(selection))
        destruct_object(tree)
        tree = temp_ds
    var_set = ROOT.RooArgSet()
    var_list = {}
    for var in variables:
        var_list[var] = ROOT.RooRealVar(var, var, 0.0)
        var_set.add(var_list[var])
    dataset = ROOT.RooDataSet(name, title, var_set, ROOT.RooFit.Import(tree))
    if weight_var:
        # Weights to normalize
        to_normalize_w = ROOT.RooFormulaVar("{}_not_normalized".format(weight_var),
                                            "{}_not_normalized".format(weight_var),
                                            "*".join(weights_to_normalize),
                                            list_to_rooarglist(var_list[weight] for weight in weights_to_normalize))
        var_set.append(to_normalize_w)
        dataset.addColumn(to_normalize_w)
        sum_weights = sum(dataset.get(entry)["{}_not_normalized".format(weight_var)].getVal()
                          for entry in dataset.sumEntries())
        normalized_w = ROOT.RooFormulaVar("{}_normalized".format(weight_var),
                                          "{}_normalized".format(weight_var),
                                          "{}_not_normalized/{}".format(weight_var, sum_weights),
                                          ROOT.RooArgList(to_normalize_w))
        var_set.append(normalized_w)
        dataset.addColumn(normalized_w)
        # Non-normalized weights
        weights = ROOT.RooFormulaVar(weight_var,
                                     weight_var,
                                     "*".join(weights_not_to_normalize + ["{}_normalized".format(weight_var)]),
                                     list_to_rooarglist([var_list[weight] for weight in weights_not_to_normalize] +
                                                        [normalized_w]))
        var_set.append(weights)
        dataset.addColumn(weights)
        dataset_w = ROOT.RooDataSet(name, title, var_set,
                                    ROOT.RooFit.Import(dataset),
                                    ROOT.RooFit.WeightVar(weight_var))
        destruct_object(dataset)
        dataset = dataset_w
    # ROOT Cleanup
    tfile.Close()
    destruct_object(tree)
    destruct_object(tfile)
    if selection:
        for leave in leave_list:
            destruct_object(leave)
    for var in variables:
        destruct_object(var_list[var])
    # Let's return
    dataset.SetName(name)
    dataset.SetTitle(title)
    return dataset


def get_pandas_from_root_file(file_name, tree_name, kwargs):
    """Load a pandas DataFrame from a ROOT file.

    Optional keys in `kwargs` are:
        + `variables`: List of variables to load.
        + `selection`: Selection to apply.

    Arguments:
        file_name (str): File to load.
        tree_name (str): Tree to load.
        **kwargs (dict): Extra configuration.

    Returns:
        pandas.DataFrame: ROOT file converted to pandas.

    """
    logger.debug("Loading ROOT file in pandas format -> %s:%s",
                 file_name, tree_name)
    if not os.path.exists(file_name):
        raise OSError("Cannot find input file -> {}".format(file_name))
    selection = kwargs.get('selection', None)
    variables = kwargs.get('variables', None)
    if selection:
        output_data = read_root(file_name, tree_name).query(selection)
        if variables:
            output_data = output_data[variables]
    else:
        output_data = read_root(file_name, tree_name, columns=variables)
    return output_data


# EOF
