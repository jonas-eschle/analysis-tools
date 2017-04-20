#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   converters.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.04.2017
# =============================================================================
"""Convert from Pandas to ROOT."""

from collections import defaultdict

import pandas as pd
import ROOT


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


# EOF
