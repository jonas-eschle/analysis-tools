#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   acceptance.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   21.03.2017
# =============================================================================
"""Acceptance class."""

import numpy as np


class Acceptance(object):
    """Selection acceptance."""

    def __init__(self, var_list, gen_efficiency, reco_efficiency):
        """Initialize the variables.

        Arguments:
            var_list (list[str]): Name of the variables the acceptance depends on.
            gen_efficiency (`analysis.efficiency.Efficiency`): Generator level efficiency.
            reco_efficiency (`analysis.efficiency.Efficiency`): Reconstructed efficiency.

        Raises:
            KeyError: If the variable names don't match.

        """
        self._var_list = var_list
        self._generation = gen_efficiency
        if set(gen_efficiency.get_variables()) != set(var_list):
            raise KeyError("Non-matching variable names in generation")
        self._reconstruction = reco_efficiency
        if set(reco_efficiency.get_variables()) != set(var_list):
            raise KeyError("Non-matching variable names in reconstruction")

    def apply_accept_reject(self, data, inplace=False, weight_col='acc_weights'):
        """Apply the accept-reject method to filter an input data frame.

        Arguments:
            data (`pandas.DataFrame`): Data to filter.
            inplace (bool, optional): Modify the input data frame to add the weights?
                Defaults to False.
            weight_col (str, optional): Name of the weights column to be added.
                Defaults to 'acc_weights'.

        Returns:
            `pandas.DataFrame`: Filtered data frame, with the weights column added.

        Raises:
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
        data[weight_col] = self.get_weights(data)
        # pylint: disable=E1101
        return data[data[weight_col] >= np.random.uniform(high=data[weight_col].max(), size=data.shape[0])]

    def get_weights(self, data):
        """var_frame is a pandas.DataFrame with the columns.

        Column names are taken from var_list.
        Returns a pandas.Series.

        """
        gen_eff = self._generation.get_efficiency(data[self._var_list])
        reco_eff = self._reconstruction.get_efficiency(data[self._var_list])
        return reco_eff/gen_eff


# EOF
