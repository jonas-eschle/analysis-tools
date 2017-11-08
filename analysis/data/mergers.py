#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   mergers.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   26.04.2017
# =============================================================================
"""Merge datasets."""

import pandas as pd
import ROOT

from analysis.utils.root import rooargset_to_set, destruct_object


def merge(data_list, **kwargs):
    """Merge data sets.

    Arguments:
        data_list (list): Datasets to merge.
        **kwargs (dict): Configuration options. In case of `ROOT.RooDataSet`, we need
            to include the `name` of the merged dataset, and optionally its `title`.

    Return:
        dataset.

    Raise:
        ValueError: When the datasets are of different types or cannot be merged.
        AttributeError: When the datasets are of unknown type.
        KeyError: When some configuration is missing.

    """
    if not len(set(type(dataset) for dataset in data_list)) == 1:
        raise ValueError("Incompatible dataset types")
    if isinstance(data_list[0], ROOT.TObject):
        if 'name' not in kwargs:
            raise KeyError("No name specified for dataset merging.")
        return merge_root(data_list, kwargs['name'], kwargs.get('title', kwargs['name']))
    elif isinstance(data_list[0], (pd.DataFrame, pd.Series)):
        raise NotImplementedError()
        # return merge_pandas(data_list)
    else:
        raise AttributeError("Unknown dataset type -> {}".format(type(data_list[0])))


def merge_root(data_list, name=None, title=None, destruct_data=True):
    """Merge RooDataSets.

    Arguments:
        name (str): Dataset name.
        name (str): Dataset title.
        data_list (list[ROOT.RooDataSet]): Datasets to merge.

    Return:
        ROOT.RooDataSet: Merged dataset.

    Raise:
        ValueError: If the datasets are incompatible.
        KeyError: If some keyword argument is missing

    """
    # Cross check variables
    variables = set(var.GetName() for var in rooargset_to_set(data_list[0].get()))
    if any([set(var.GetName() for var in rooargset_to_set(dataset.get())) != variables
            for dataset in data_list]):
        raise ValueError("Incompatible observables")
    # Check weights
    if len(set(data.isWeighted() for data in data_list)) > 1:
        raise ValueError("Input dataset list contains weighted and uneweighted datasets.")
    # Merge by append, since we don't know the original weight situation
    output_ds = data_list.pop(0)
    for data in data_list:
        output_ds.append(data)
        if destruct_data:
            destruct_object(data)
    return output_ds


def merge_pandas(data_list):
    """Merge pandas data frames.

    Arguments:
        data_list (list[pandas.DataFrame]): Datasets to merge.

    Return:
        pandas.DataFrame: Merged dataset.

    Raise:
        ValueError: If the datasets are incompatible.

    """
    pass

# EOF
