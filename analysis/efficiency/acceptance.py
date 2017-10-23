#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   acceptance.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   21.03.2017
# =============================================================================
"""Acceptance class."""
from __future__ import print_function, division, absolute_import

import numpy as np


class Acceptance(object):
    """Selection acceptance."""

    def __init__(self, var_list, gen_efficiency, reco_efficiency):
        """Initialize the variables.

        Arguments:
            var_list (list[str]): Name of the variables the acceptance depends on.
            gen_efficiency (`analysis.efficiency.Efficiency`): Generator level efficiency.
            reco_efficiency (`analysis.efficiency.Efficiency`): Reconstructed efficiency.

        Raise:
            KeyError: If the variable names don't match.

        """
        self._var_list = var_list
        self._generation = gen_efficiency
        if set(gen_efficiency.get_variables()) != set(var_list):
            raise KeyError("Non-matching variable names in generation")
        self._reconstruction = reco_efficiency
        if set(reco_efficiency.get_variables()) != set(var_list):
            raise KeyError("Non-matching variable names in reconstruction")

    def apply_accept_reject(self, data, inplace=False, weight_col=None):
        """Apply the accept-reject method to filter an input data frame.

        Arguments:
            data (`pandas.DataFrame`): Data to filter.
            inplace (bool, optional): Modify the input data frame to add the weights?
                Defaults to False.
            weight_col (str, optional): Name of the weights column to be added.
                Defaults to None, in which case the column is not added.

        Return:
            `pandas.DataFrame`: Filtered data frame, with the weights column added.

        Raise:
            KeyError: If the weight column name already exists in the dataset.
            ValueError: If the acceptance variables cannot be found in the data frame.

        """
        # Cross check
        if weight_col in data.columns:
            raise KeyError("Weight column already present in the input data frame")
        if not set(self._var_list).issubset(set(data.columns)):
            raise ValueError("Acceptance variables not present in the input data frame")
        # Copy the original data to leave it untouched
        if not inplace:
            data = data.copy()
        # Calculate event by event weights
        weights = self.get_gen_weights(data)
        # pylint: disable=E1101
        filtered_data = data[weights >= np.random.uniform(high=weights.max(), size=data.shape[0])]
        if weight_col:
            filtered_data[weight_col] = weights
        return filtered_data

    def get_gen_weights(self, data):
        """var_frame is a pandas.DataFrame with the columns.

        Returns reco/gen.

        Column names are taken from var_list.
        Returns a pandas.Series.

        """
        gen_eff = self._generation.get_efficiency(data[self._var_list])
        reco_eff = self._reconstruction.get_efficiency(data[self._var_list])
        return reco_eff/gen_eff

    def get_fit_weights(self, data):
        """var_frame is a pandas.DataFrame with the columns.

        Returns gen/reco and normalizes to the data size.

        Column names are taken from var_list.
        Returns a pandas.Series.

        """
        gen_eff = self._generation.get_efficiency(data[self._var_list])
        reco_eff = self._reconstruction.get_efficiency(data[self._var_list])
        weights = (gen_eff/reco_eff).replace([-np.inf, np.inf, np.nan], 0.0)
        return weights * data.shape[0] / weights.sum()


# EOF
