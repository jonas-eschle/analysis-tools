#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   efficiency.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   21.03.2017
# =============================================================================
"""Efficiency class."""
from __future__ import print_function, division, absolute_import

import re
from collections import OrderedDict

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import sys

from analysis.utils.paths import get_efficiency_path, work_on_file
from analysis.utils.config import write_config
from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.efficiency')


class Efficiency(object):
    """Represent an efficiency object."""

    MODEL_NAME = ''

    def __init__(self, var_list, config):
        """Initialize the internal configuration.

        A `rename-vars` dictionary the `config` dictionary can be used to specify the
        expected name (in the data, in the ranges) of some of the variables in `var_list`.

        Arguments:
            var_list (list): List of observables to apply the efficiency to.
            config (dict): Efficiency model configuration.

        """
        self._var_names = OrderedDict((var, var) for var in var_list)
        if 'rename-vars' in config:
            self.rename_variables(config.pop('rename-vars'))
        self._config = config

    def get_variables(self):
        """Get list of variables.

        Return:
            list: Variables in the correct order.

        """
        return list(self._var_names.values())

    def get_variable_names(self):
        """Get variable names.

        Return:
            OrderedDict: Map efficiency var -> var name

        """
        return self._var_names

    def rename_variables(self, name_map):
        """Rename the variables.

        Arguments:
            name_map (dict): Map old -> new variable names.

        Return:
            list: New variable list.

        Raise:
            KeyError: If one of the keys of the map is not found in the variable list.

        """
        for old_name, new_name in name_map.items():
            try:
                self._var_names[old_name] = new_name
            except ValueError:
                raise KeyError("Cannot find variable name -> {}".format(old_name))

    def get_efficiency(self, data):
        """Get the efficiency for the given event or dataset.

        Arguments:
            data (`pandas.DataFrame` or Sequence): Data to calculate the efficiency of.

        Return:
            pandas.Series: Per-event efficiencies.

        Raise:
            ValueError: If the data format is not correct, eg, there is a variable mismatch.

        """
        var_list = self.get_variables()
        if not isinstance(data, pd.DataFrame):
            if len(var_list) != len(data):
                raise ValueError("Input data length does not match with the efficiency variables")
            data = pd.DataFrame(data, columns=var_list)
        if not set(var_list).issubset(set(data.columns)):
            raise ValueError("Missing variables in the input data")
        return self._get_efficiency(data[var_list].copy()).clip(lower=0.0)

    def get_randomized_efficiency(self, data):
        """Get the efficiency for the given event or dataset Gaussianly randomized by its uncertainty.

        Arguments:
            data (`pandas.DataFrame` or Sequence): Data to calculate the efficiency of.

        Return:
            pandas.Series: Per-event efficiencies.

        Raise:
            ValueError: If the data format is not correct, eg, there is a variable mismatch.
            KeyError: If there errors are not present and randomization cannot be applied.

        """
        var_list = self.get_variables()
        if not isinstance(data, pd.DataFrame):
            if len(var_list) != len(data):
                raise ValueError("Input data length does not match with the efficiency variables")
            data = pd.DataFrame(data, columns=var_list)
        if not set(var_list).issubset(set(data.columns)):
            raise ValueError("Missing variables in the input data")
        try:
            return self._get_efficiency(data[var_list].copy(), randomize=True).clip(lower=0.0)
        except ValueError as error:
            logger.error("Cannot randomize efficiency: %s", error)
            raise KeyError

    def _get_efficiency(self, data, randomize=False):
        """Calculate the efficiency.

        Note:
            No variable checking is performed.

        Arguments:
            data (`pandas.DataFrame`): Data to apply the efficiency to.
            randomize (bool, optional): Apply Gaussian randomization to the efficiencies?
                Defaults to False.

        """
        raise NotImplementedError()

    def get_efficiency_errors(self, data):
        """Get the efficiency error for the given event or dataset.

        Arguments:
            data (`pandas.DataFrame` or Sequence): Data to calculate the efficiency errors of.

        Return:
            pandas.Series: Per-event efficiency errors.

        Raise:
            ValueError: If the data format is not correct, eg, there is a variable mismatch.

        """
        var_list = self.get_variables()
        if not isinstance(data, pd.DataFrame):
            if len(var_list) != len(data):
                raise ValueError("Input data length does not match with the efficiency variables")
            data = pd.DataFrame(data, columns=var_list)
        if not set(var_list).issubset(set(data.columns)):
            raise ValueError("Missing variables in the input data")
        return self._get_efficiency_error(data[var_list].copy()).clip(lower=0.0)

    def _get_efficiency_error(self, data):
        """Calculate the efficiency error.

        Note:
            No variable checking is performed.

        Arguments:
            data (`pandas.DataFrame`): Data to calculate the efficiency errors of.

        """
        raise NotImplementedError()

    def plot(self, data, weight_var=None, labels=None):
        """Plot the efficiency against a dataset.

        Arguments:
            data (`pandas.DataFrame`): Data to plot.
            weight_var (str, optional): Variable to use as weight. If `None`
                is given, unity weights are used.
            labels (dict, optional): Label names for each variable.

        Return:
            dict: Variable -> plot mapping.

        Raise:
            ValueError: If the weight variable is not in `data`.

        """
        def tex_escape(text):
            """Escape LaTeX characters.

            Arguments:
                text (str): Text to escape.

            Return:
                str: Escaped message.

            """
            conv = {'&': r'\&',
                    '%': r'\%',
                    '$': r'\$',
                    '#': r'\#',
                    '_': r'\_',
                    '{': r'\{',
                    '}': r'\}',
                    '~': r'\textasciitilde{}',
                    '^': r'\^{}',
                    '\\': r'\textbackslash{}',
                    '<': r'\textless',
                    '>': r'\textgreater'}
            escape_chars = []
            for key in sorted(list(conv.keys()), key=lambda item: -len(item)):
                # python 2/3 compatibility layer, alt: from builtins import str
                if sys.version_info[0] < 3:
                    escape_chars.append(unicode(key))
                else:
                    escape_chars.append(str(key))
            regex = re.compile('|'.join(escape_chars))
            return regex.sub(lambda match: conv[match.group()], text)

        if weight_var and weight_var not in data.columns:
            raise ValueError("The weight variable is not find in the dataset -> {}".format(weight_var))
        if labels is None:
            labels = {}
        figures = {}
        for var_name in self.get_variables():
            x, y = self.project_efficiency(var_name, n_points=1000)
            fig = plt.figure()
            data_to_plot = data[var_name]*data[weight_var] if weight_var else data[var_name]
            sns.distplot(data_to_plot, kde=None, norm_hist=True)
            plt.plot(x, y, 'b-')
            if var_name not in labels:
                labels[var_name] = tex_escape(var_name)
            plt.xlabel(labels[var_name])
            figures[var_name] = fig
        return figures

    def project_efficiency(self, var_name, n_points):
        """Project the efficiency in one variable.

        If multidimensional, the non-projected variables need to be integrated out.

        Arguments:
            var_name (str): Variable to project.
            n_points (int): Number of points of the projection.

        Return:
            tuple (np.array): x and y coordinates of the projection.

        Raise:
            ValueError: If the requested variable is not modeled by the efficiency object.

        """
        raise NotImplementedError()

    @staticmethod
    def fit(dataset, var_list, weight_var=None, **params):
        """Model the data using the Efficiency model.

        Arguments:
            dataset (pandas.DataFrame): Data to model.
            var_list (list): Variables to model. Defines the order.
            weight_var (str, optional): Variable to use as weight. If `None`
                is given, unity weights are used.
            **params (dict): Extra configuration parameters. Different for
                each subclass.

        Return:
            `Efficiency`: New Efficiency object.

        """
        raise NotImplementedError()

    def write_to_disk(self, name, link_from=None):
        """Write efficiency object to disk.

        Arguments:
            name (str): Name of the efficiency object.
            link_from (str, optional): Storage to link from. Defaults to
                no link.

        Return:
            str: Path of the output file.

        """
        if not self.MODEL_NAME:
            raise NotImplementedError("Cannot save generic Efficiency")
        with work_on_file(name, get_efficiency_path, link_from) as file_name:
            write_config({'model': self.MODEL_NAME,
                          'variables': self.get_variables(),
                          'parameters': self._config},
                         file_name)
        return file_name

# EOF
