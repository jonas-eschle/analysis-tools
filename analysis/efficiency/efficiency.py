#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   efficiency.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   21.03.2017
# =============================================================================
"""Efficiency class."""

import pandas as pd

from analysis.utils.paths import get_efficiency_path, work_on_file
from analysis.utils.config import write_config


class Efficiency(object):
    """Represent an efficiency object."""

    MODEL_NAME = ''

    def __init__(self, var_list, config):
        """Initialize the internal configuration.

        Arguments:
            var_list (list): List of observables to apply the efficiency to.
            config (dict): Efficiency model configuration.

        """
        self._var_list = var_list
        self._config = config

    def rename_variables(self, name_map):
        """Rename the variables.

        Arguments:
            name_map (dict): Map old -> new variable names.

        Returns:
            list: New variable list.

        Raises:
            KeyError: If one of the keys of the map is not found in the variable list.

        """
        for old_name, new_name in name_map.items():
            try:
                self._var_list[self._var_list.index(old_name)] = new_name
            except ValueError:
                raise KeyError("Cannot find variable name -> %s" % old_name)

    def get_variables(self):
        """Get the variable list.

        Returns:
            list: Efficiency variables.

        """
        return self._var_list

    def get_efficiency(self, data):
        """Get the efficiency for the given event or dataset.

        Arguments:
            data (`pandas.DataFrame` or Sequence): Data to calculate the efficiency of.

        Returns:
            pandas.Series: Per-event efficiencies.

        Raises:
            ValueError: If the data format is not correct, eg, there is a variable mismatch.

        """
        if not isinstance(data, pd.DataFrame):
            if len(self._var_list) != len(data):
                raise ValueError("Input data length does not match with the efficiency variables")
            data = pd.DataFrame(data, columns=self._var_list)
        if not set(self._var_list).issubset(set(data.columns)):
            raise ValueError("Missing variables in the input data")
        return self._get_efficiency(data[self._var_list].copy())

    def _get_efficiency(self, data):
        """Calculate the efficiency.

        Note:
            No variable checking is performed.

        Arguments:
            data (`pandas.DataFrame`): Data to apply the efficiency to.

        """
        raise NotImplementedError()

    def plot(self, data, labels=None):
        """Plot the efficiency against a dataset.

        Arguments:
            data (`pandas.DataFrame`): Data to plot.
            labels (dict, optional): Label names for each variable.

        Returns:
            dict: Variable -> plot mapping.

        """
        raise NotImplementedError()

    @staticmethod
    def fit(dataset, var_list, **params):
        """Model the data using the Efficiency model.

        Arguments:
            dataset (pandas.DataFrame): Data to model.
            var_list (list): Variables to model. Defines the order.
            **params (dict): Extra configuration parameters. Different for
                each subclass.

        Returns:
            `Efficiency`: New Efficiency object.

        """
        raise NotImplementedError()

    def write_to_disk(self, name, link_from=None):
        """Write efficiency object to disk.

        Arguments:
            name (str): Name of the efficiency object.
            link_from (str, optional): Storage to link from. Defaults to
                no link.

        Returns:
            str: Path of the output file.

        """
        if not self.MODEL_NAME:
            raise NotImplementedError("Cannot save generic Efficiency")
        with work_on_file(name, link_from, get_efficiency_path) as file_name:
            write_config({'model': self.MODEL_NAME,
                          'variables': self._var_list,
                          'parameters': self._config},
                         file_name)
        return file_name

# EOF
