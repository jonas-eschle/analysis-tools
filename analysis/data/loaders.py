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

import pandas as pd
from root_pandas import read_root

from analysis.data.converters import dataset_from_pandas
from analysis.utils.logging_color import get_logger
from analysis.utils.root import destruct_object


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
        output_data = store.select(tree_name,
                                   columns=variables,
                                   where=selection)
    return output_data


def get_pandas_from_pandas_file(file_name, tree_name, kwargs):
    """Load a pandas DataFrame from HDF file.

    Optional keys in `kwargs` are:
        + `variables`: List of variables to load.

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
        + `weight-var`: Variable defining a weight.

    Arguments:
        file_name (str): File to load.
        tree_name (str): Tree to load.
        **kwargs (dict): Extra configuration.

    Raises:
        KeyError: If there are missing variables in `kwargs`.

    """
    logger.debug("Loading pandas file in RooDataSet format -> %s:%s",
                 file_name, tree_name)
    # Checks and variable preparation
    try:
        name = kwargs['name']
        title = kwargs['title']
    except KeyError as error:
        raise KeyError("Missing configuration key -> %s" % error)
    # Load the data
    frame = _load_pandas(file_name, tree_name,
                         kwargs.get('variables', None),
                         kwargs.get('selection', None))
    # Convert it
    return dataset_from_pandas(frame, name, title,
                               var_list=kwargs.get('variables', None),
                               weight_var=kwargs.get('weight-var', None),
                               category=kwargs.get('category', None))


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
    if variables - leaves:
        raise ValueError("Cannot find leaves in input -> %s" % variables - leaves)
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
    name = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits)
                   for _ in range(10))
    dataset = ROOT.RooDataSet(name, name, var_set, ROOT.RooFit.Import(tree))
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
    return read_root(file_name, tree_name,
                     columns=kwargs.get('variables', None),
                     where=kwargs.get('selection', None))


# EOF
