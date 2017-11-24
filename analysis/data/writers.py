#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   writers.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   22.11.2017
# =============================================================================
"""Tools to write datasets to disk."""

import os

import pandas as pd
import ROOT

from analysis.utils.pdf import load_pdf_by_name
from analysis.utils.root import iterate_roocollection, destruct_object
from analysis.data.converters import dataset_from_pandas, pandas_from_dataset


def write_dataset(file_name, dataset):
    """Write the dataset to a file.

    Output format is decided by the extension of the output file name, and appropriate
    conversions are done whenever needed.

    Arguments:
        file_name (str): Output file name.
        dataset (ROOT.RooDataSet or pandas.DataFrame): Dataset to write.

    Raise:
        OSError: If the output file exists.

    """
    if os.path.exists(file_name):
        raise OSError("Output file exists -> {}".format(file_name))
    ext = os.path.splitext(file_name)[1]
    if ext in ('.h5', '.hdf'):
        write_hdf(file_name, dataset)
    elif ext in '.root':
        write_root(file_name, dataset)
    else:
        raise RuntimeError


def write_hdf(file_name, dataset):
    """Write HDF file.

    Input dataset is converted to a pandas DataFrame and `to_hdf` is used. The
    key of the dataset is `data`.

    Arguments:
        file_name (str): Output file name.
        dataset (ROOT.RooDataSet or pandas.DataFrame): Dataset to write.

    """
    if isinstance(dataset, ROOT.RooDataSet):
        dataset = pandas_from_dataset(dataset)
    pd.to_hdf(file_name, "data")


def write_root(file_name, dataset):
    """Write HDF file.

    Input dataset is converted to a TTree with name `data` and then written out in a `TFile`.

    Arguments:
        file_name (str): Output file name.
        dataset (ROOT.RooDataSet or pandas.DataFrame): Dataset to write.

    """
    if isinstance(dataset, pd.DataFrame):
        dataset = dataset_from_pandas(dataset, "data", "data")
    storer = load_pdf_by_name('RooDataSetToTree')
    output_file = ROOT.TFile.Open(file_name, "NEW")
    tree = storer(dataset, "data", "data",
                  ','.join(var.GetName() for var in iterate_roocollection(dataset.get())),
                  True)
    tree.Write("", True)
    # output_file.Write()
    output_file.Close()
    destruct_object(tree)
    destruct_object(output_file)

# EOF
