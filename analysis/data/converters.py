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
from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.data.converters')


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


def dataset_from_pandas(frame, name, title, var_list=None, weight_var=None, categories=None):
    """Build RooDataset from a Pandas DataFrame.

    Arguments:
        frame (pandas.DataFrame): DataFrame to convert.
        name (str): RooDataSet name.
        title (str): RooDataSet title.
        var_list (list[str], optional): List of variables to add to the dataset.
            If not given, all variables are converted.
        weight_var (str, optional): Assign the given variable name as weight.
            Defaults to None.
        categories (list[`ROOT.RooCategory`], optional): Categories to separate the data in.
            Their name must correspond to a column in the `frame`.

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
            for cat_name in cat_names:
                var_set.setCatLabel(cat_name, row[cat_name])
            dataset.add(var_set)
        return dataset

    if weight_var and weight_var not in frame.columns:
        raise KeyError("Cannot find weight variable -> {}".format(weight_var))
    var_names = var_list if var_list else list(frame.columns)
    cat_names = []
    roovar_list = []
    if categories:
        for category in categories:
            cat_var = category.GetName()
            if cat_var not in frame.columns:
                raise KeyError("Cannot find category variable -> {}".format(cat_var))
            roovar_list.append(category)
            if cat_var in var_names:
                var_names.pop(var_names.index(cat_var))
            cat_names.append(cat_var)
        super_category = 'x'.join(cat.GetName() for cat in categories)
        if super_category in var_names:
            logger.warning("You asked for variable %s but this is the name of a SuperCategory. Ignoring it.",
                           super_category)
            var_names.pop(var_names.index(super_category))
    roovar_list.extend([ROOT.RooRealVar(var_name, var_name, 0.0) for var_name in var_names])
    dataset_set = list_to_rooargset(roovar_list)
    dataset = fill_dataset(name, title, dataset_set, frame)
    if weight_var:
        dataset = ROOT.RooDataSet(name, title, dataset_set,
                                  ROOT.RooFit.Import(dataset),
                                  ROOT.RooFit.WeightVar(weight_var))
    return dataset


# EOF
