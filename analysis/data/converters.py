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

from analysis.utils.root import list_to_rooargset


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


def dataset_from_pandas(frame, name, title, var_list=None, weight_var=None, category=None):
    """Build RooDataset from a Pandas DataFrame.

    Arguments:
        frame (pandas.DataFrame): DataFrame to convert.
        name (str): RooDataSet name.
        title (str): RooDataSet title.
        var_list (list[str], optional): List of variables to add to the dataset.
            If not given, all variables are converted.
        weight_var (str, optional): Assign the given variable name as weight.
            Defaults to None.
        category (`ROOT.RooCategory`, optional): Category to separate the data in. Its name
            must correspond to a column in the `frame`.

    Returns:
        ROOT.RooDataSet: Frame converted to dataset.

    Raises:
        KeyError: If the weight_var or the category is not present in `frame`.

    """
    def fill_dataset(name, title, var_set, input_data):
        """Fill a dataset from a pandas DataFrame.

        Arguments:
            name (str): Name of the dataset.
            title (str): Title of the dataset.
            var_set (ROOT.RooArgSet): Variables in the dataset.
            input_data (pandas.DataFrame): Input data.

        Returns:
            ROOT.RooDataSet: Output data set.

        """
        dataset = ROOT.RooDataSet(name, title, var_set)
        for _, row in input_data.iterrows():
            for var_name in var_names:
                if isinstance(row[var_name], (float, int)):
                    var_set.setRealValue(var_name, row[var_name])
            dataset.add(var_set)
        return dataset

    if weight_var and weight_var not in frame.columns:
        raise KeyError("Cannot find weight variable -> %s" % weight_var)
    if category:
        cat_var = category.GetName()
        if cat_var not in frame.columns:
            if 'category' in frame.columns:
                cat_var = 'category'
            else:
                raise KeyError("Cannot find category variable -> %s" % cat_var)
    var_names = var_list if var_list else list(frame.columns)
    dataset_set = list_to_rooargset(ROOT.RooRealVar(var_name, var_name, 0.0)
                                    for var_name in var_names)
    categories = frame.groupby(cat_var).indices.keys() \
        if category else []
    if categories:
        dataset = None
        for category in categories:
            temp_ds = ROOT.RooDataSet(name, name,
                                      dataset_set,
                                      ROOT.RooFit.Index(category),
                                      ROOT.RooFit.Import(category,
                                                         fill_dataset('%s_%s' % (name, category),
                                                                      '%s_%s' % (name, category),
                                                                      dataset_set,
                                                                      frame[cat_var == category])))
            if dataset is None:
                dataset = temp_ds
            else:
                dataset.append(temp_ds)
    else:
        dataset = fill_dataset(name, title, dataset_set, frame)
    if weight_var:
        dataset = ROOT.RooDataSet(name, title, dataset_set,
                                  ROOT.RooFit.Import(dataset),
                                  ROOT.RooFit.WeightVar(weight_var))
    return dataset


# EOF
