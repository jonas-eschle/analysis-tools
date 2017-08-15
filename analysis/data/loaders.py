#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   loaders.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.04.2017
# =============================================================================
"""Data loaders."""

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
# Load pandas files
###############################################################################
def _load_pandas(file_name, tree_name, variables, selection):
    """Load the pandas dataset.

    Arguments:
        file_name (str): File to load.
        tree_name (str): Tree to load.
        variables (list): List of variables to load (speeds up loading).
        selection (str): Not used right now.

    Raises:
        OSError: If the input file does not exist.
        KeyError: If the tree is not found or some of the requested branches are missing.

    """
    if not os.path.exists(file_name):
        raise OSError("Cannot find input file -> %s" % file_name)
    with pd.HDFStore(file_name, 'r') as store:
        if tree_name not in store:
            raise KeyError("Cannot find tree in input file -> %s" % tree_name)
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
        + `weights`: Variables defining the weight.
        + `weight_var`: Name of the weight variable. If there is only one weight,
            it is not needed. Otherwise it has to be specified.
        + `categories`: RooCategory variables to use.

    Arguments:
        file_name (str): File to load.
        tree_name (str): Tree to load.
        **kwargs (dict): Extra configuration.

    Raises:
        KeyError: If there are missing variables in `kwargs`.
        ValueError: If there is an error in loading the acceptance.

    """
    logger.debug("Loading pandas file in RooDataSet format -> %s:%s",
                 file_name, tree_name)
    # Checks and variable preparation
    try:
        name = kwargs['name']
        title = kwargs.get('title', name)
    except KeyError as error:
        raise KeyError("Missing configuration key -> %s" % error)
    # Check weights
    weights = kwargs.get('weights', [])
    weight_var = kwargs.get('weight_var', None)
    if not isinstance(weights, (list, tuple)):
        weights = [weights]
    if weights:
        if not weight_var:
            if len(weights) == 1:
                weight_var = weights[0]
            else:
                raise KeyError("Missing name of the weight variable")
    elif weight_var:
        if not weights:
            weights = [weight_var]
    # Variables
    var_list = kwargs.get('variables', None)
    acc_var = None
    if weights:
        if 'acceptance' in kwargs:
            if 'acceptance_fit' in weights:
                acc_var = 'acceptance_fit'
            if 'acceptance_gen' in weights:
                if acc_var:
                    raise ValueError("Specified both 'acceptance_fit' and 'acceptance_gen' as weights.")
                acc_var = 'acceptance_gen'
            if not acc_var:
                logger.warning("Requested acceptance but it has not been specified as a weight to use. Ignorning.")
        if var_list:
            var_list = list(set(var_list) | set(weights))
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
            raise ValueError("Name clash: the column 'acceptance_fit' is present in the dataset")
        if acc_var == 'acceptance_fit':
            frame['acceptance_fit'] = acceptance.get_fit_weights(frame)
        else:
            frame['acceptance_gen'] = acceptance.get_gen_weights(frame)
    # Apply weights, normalizing them
    if weight_var:
        frame[weight_var] = np.prod([frame[w_var] for w_var in weights], axis=0)
        frame[weight_var] = frame[weight_var]/frame[weight_var].sum()*frame.shape[0]
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
        raise OSError("Cannot find input file -> %s" % file_name)
    try:
        name = kwargs['name']
        title = kwargs.get('title', name)
    except KeyError as error:
        raise KeyError("Missing configuration key -> %s" % error)
    tfile = ROOT.TFile.Open(file_name)
    tree = tfile.Get(tree_name)
    if not tree:
        raise KeyError("Cannot find tree in input file -> %s" % tree_name)
    leaves = set(get_list_of_leaves(tree))
    variables = set(kwargs.get('variables', leaves))
    # Acceptance
    if 'acceptance' in kwargs:
        raise NotImplementedError("Acceptance weights are not implemented for ROOT files")
    # Check weights
    weights = kwargs.get('weights', None)
    weight_var = kwargs.get('weight_var', None)
    if not (isinstance(weights, (list, tuple)) or weights is None):
        weights = [weights]
    if weights:
        if not weight_var:
            if len(weights) == 1:
                weight_var = weights[0]
            else:
                raise KeyError("Missing name of the weight variable")
    elif weight_var:
        if not weights:
            weights = [weight_var]
    if weights:
        variables = set(variables) | set(weights)
    # Crosscheck leaves
    if variables - leaves:
        raise ValueError("Cannot find leaves in input -> %s" % (variables - leaves))
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
    var_list = []
    for var in variables:
        var_list.append(ROOT.RooRealVar(var, var, 0.0))
        var_set.add(var_list[-1])
    dataset = ROOT.RooDataSet(name, title, var_set, ROOT.RooFit.Import(tree))
    if weights:
        non_normalized_w = ROOT.RooFormulaVar("%s_not_normalized" % weight_var,
                                              "%s_not_normalized" % weight_var,
                                              "*".join(weights),
                                              list_to_rooarglist(weights))
        var_set.append("%s_not_normalized" % weight_var)
        dataset.addColumn(non_normalized_w)
        sum_weights = sum(dataset.get(entry)["%s_not_normalized" % weight_var].getVal()
                          for entry in dataset.sumEntries())
        normalized_w = ROOT.RooFormulaVar(weight_var, weight_var,
                                          "%s_not_normalized/%s" % (weight_var, sum_weights),
                                          ROOT.RooArgList(non_normalized_w))
        var_set.append(weight_var)
        dataset.addColumn(normalized_w)
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
        destruct_object(var_list)
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
        raise OSError("Cannot find input file -> %s" % file_name)
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
