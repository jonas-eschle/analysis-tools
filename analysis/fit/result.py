#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   result.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   19.05.2017
# =============================================================================
"""Analyze and store fit results."""
from __future__ import print_function, division, absolute_import

import copy
from collections import OrderedDict

import numpy as np

# from analysis.utils.decorators import memoize
import analysis.utils.paths as _paths
from analysis.utils.config import load_config, write_config
from analysis.utils.exceptions import NotInitializedError, ConfigError
from analysis.utils.root import iterate_roocollection

_SUFFIXES = ('', '_err_hesse', '_err_minus', '_err_plus')

# Minuit covariance codes
COV_CODES = {-1: "Not available (inversion failed or Hesse failed)",
             0: "Not positive defined",
             1: "Only approximate",
             2: "Forced pos def",
             3: "Full accurate matrix"}

STATUS = {'MINIMIZE': {0: "Converged",
                       1: "Covariance was made pos defined",
                       2: "Hesse is invalid",
                       3: "EDM is above max",
                       4: "Reached call limit",
                       5: "Other failure"},
          'HESSE': {0: "Converged",
                    1: "Hesse failed",
                    2: "Matrix inversion failed",
                    3: "Matrix is not pos defined"},
          'MINOS': {0: "Converged",
                    1: "Maximum number of function calls exceeded when running for lower error",
                    2: "Maximum number of function calls exceeded when running for upper error",
                    3: "New minimum found when running for lower error",
                    4: "New minimum found when running for upper error",
                    5: "Other failure"}}


def ensure_initialized(method):
    """Make sure the fit result is initialized."""

    def wrapper(self, *args, **kwargs):
        """Check result is empty. Raise otherwise."""
        if not self.get_result():
            raise NotInitializedError("Trying to export a non-initialized fit result")
        return method(self, *args, **kwargs)

    return wrapper


class FitResult(object):
    """Manager for fit results.

    Transforms `RooFitResult`s into something easier to manage and
    allows to save them into YAML format.

    """

    def __init__(self, result=None):
        """Initialize internal variables.

        Arguments:
            result (dict, optional): Fit result. Defaults to `None`.

        Raise:
            ValueError: If `result` is not of the correct type.

        """
        if result is not None and not isinstance(result, (dict, OrderedDict)):
            raise ValueError("result is not of the proper type")
        if result and 'const-parameters' not in result:
            result['const-parameters'] = OrderedDict()
        self._result = result

    def get_result(self):
        """Get the full fit result information.

        Return:
            dict: Full fit result information.

        """
        return self._result

    @staticmethod
    # @memoize
    def from_roofit(roofit_result):
        """Load the `RooFitResult` into the internal format.

        Arguments:
            roofit_result (`ROOT.RooFitResult`): Fit result.

        Return:
            FitResult

        """
        result = {}
        # Fit parameters
        result['const-parameters'] = OrderedDict((fit_par.GetName(), fit_par.getVal())
                                                 for fit_par
                                                 in iterate_roocollection(roofit_result.constPars()))
        result['fit-parameters'] = OrderedDict((fit_par.GetName(), (fit_par.getVal(),
                                                                    fit_par.getError(),
                                                                    fit_par.getErrorLo(),
                                                                    fit_par.getErrorHi()))
                                               for fit_par
                                               in iterate_roocollection(roofit_result.floatParsFinal()))
        result['fit-parameters-initial'] = OrderedDict((fit_par.GetName(), fit_par.getVal())
                                                       for fit_par
                                                       in iterate_roocollection(roofit_result.floatParsInit()))
        # Covariance matrix
        covariance_matrix = roofit_result.covarianceMatrix()
        cov_matrix = {'quality': roofit_result.covQual(),
                      'matrix': np.matrix([[covariance_matrix[row][col]
                                            for col in range(covariance_matrix.GetNcols())]
                                           for row in range(covariance_matrix.GetNrows())])}
        result['covariance-matrix'] = cov_matrix
        # Status
        result['status'] = OrderedDict((roofit_result.statusLabelHistory(cycle), roofit_result.statusCodeHistory(cycle))
                                       for cycle in range(roofit_result.numStatusHistory()))
        result['edm'] = roofit_result.edm()
        result['min_nll'] = roofit_result.minNll()
        return FitResult(result)

    @staticmethod
    # @memoize
    def from_yaml(yaml_dict):
        """Initialize from a YAML dictionary.

        Arguments:
            yaml_dict (dict, OrderedDict): YAML information to load.

        Return:
            FitResult

        Raise:
            KeyError: If any of the FitResult data is missing from the YAML dictionary.

        """
        if not set(yaml_dict.keys()).issuperset({'fit-parameters',
                                                 'fit-parameters-initial',
                                                 'covariance-matrix',
                                                 'status'}):
            raise KeyError("Missing keys in YAML input")
        if not set(yaml_dict['covariance-matrix'].keys()).issuperset({'quality', 'matrix'}):
            raise KeyError("Missing keys in covariance matrix in YAML input")
        # Build matrix
        yaml_dict['covariance-matrix']['matrix'] = np.asmatrix(
            np.array(yaml_dict['covariance-matrix']['matrix']).reshape(len(yaml_dict['fit-parameters']),
                                                                       len(yaml_dict['fit-parameters'])))
        return FitResult(yaml_dict)

    @staticmethod
    # @memoize
    def from_yaml_file(name):
        """Initialize from a YAML file.

        File name is determined by get_fit_result_path.

        Arguments:
            name (str): Name of the fit result.

        Return:
            self

        Raise:
            OSError: If the file cannot be found.
            KeyError: If any of the FitResult data is missing from the input file.

        """
        try:
            yaml_config = load_config(_paths.get_fit_result_path(name),
                                      validate=('fit-parameters',
                                                'fit-parameters-initial',
                                                'covariance-matrix/quality',
                                                'covariance-matrix/matrix',
                                                'status'))
            return FitResult.from_yaml(yaml_config)
        except ConfigError as error:
            raise KeyError("Missing keys in input file -> {}".format(','.join(error.missing_keys)))

    @ensure_initialized
    def to_yaml(self):
        """Convert fit result to YAML format.

        Return:
            str: Output dictionary in YAML format.

        Raise:
            NotInitializedError: If the fit result has not been initialized.

        """
        result = copy.deepcopy(self._result)
        result['covariance-matrix']['matrix'] = self._result['covariance-matrix']['matrix'].getA1()
        return result

    @ensure_initialized
    def to_yaml_file(self, name):
        """Convert fit result to YAML format.

        File name is determined by get_fit_result_path.

        Arguments:
            name (str): Name of the fit result.

        Return:
            str: Output file name.

        Raise:
            NotInitializedError: If the fit result has not been initialized.

        """
        with _paths.work_on_file(name, path_func=_paths.get_fit_result_path) as file_name:
            write_config(self.to_yaml(), file_name)
        return file_name

    @ensure_initialized
    def to_plain_dict(self, skip_cov=True):
        """Convert fit result into a pandas-friendly format.

        Blablabla

        Arguments:
            skip_cov (bool, optional): Skip the covariance matrix. Defaults to True.

        Return:
            pandas.DataFrame

        """
        pandas_dict = OrderedDict(((param_name + suffix, val)
                                   for param_name, param in self._result['fit-parameters'].items()
                                   for val, suffix in zip(param, _SUFFIXES)))
        pandas_dict.update(OrderedDict((param_name, val) for param_name, val
                                       in self._result['const-parameters'].items()))
        pandas_dict['status_migrad'] = self._result['status'].get('MIGRAD', -1)
        pandas_dict['status_hesse'] = self._result['status'].get('HESSE', -1)
        pandas_dict['status_minos'] = self._result['status'].get('MINOS', -1)
        pandas_dict['cov_quality'] = self._result['covariance-matrix']['quality']
        pandas_dict['edm'] = self._result['edm']
        pandas_dict['min_nll'] = self._result['min_nll']
        if not skip_cov:
            pandas_dict['cov_matrix'] = self._result['covariance-matrix']['matrix'].getA1()
        return pandas_dict

    @ensure_initialized
    def get_fit_parameter(self, name):
        """Get the fit parameter and its errors.

        Arguments:
            name (str): Name of the fit parameter.

        Return:
            tuple (float): Parameter value, Hesse error and upper and lower Minos errors.
                If the two latter have not been calculated, they are 0.

        Raise:
            KeyError: If the parameter is unknown.

        """
        return self._result['fit-parameters'][name]

    @ensure_initialized
    def get_const_parameter(self, name):
        """Get the const parameter.

        Arguments:
            name (str): Name of the fit parameter.

        Return:
            float: Parameter value.

        Raise:
            KeyError: If the parameter is unknown.

        """
        return self._result['const-parameters'][name]

    @ensure_initialized
    def get_fit_parameters(self):
        """Get the full list of fit parameters.

        Return:
            OrderedDict: Parameters as keys and their values and errors as values.

        """
        return self._result['fit-parameters']

    @ensure_initialized
    def get_const_parameters(self):
        """Get the full list of const parameters.

        Return:
            OrderedDict: Parameters as keys and their values and errors as values.

        """
        return self._result['const-parameters']

    @ensure_initialized
    def get_covariance_matrix(self, params=None):
        """Get the fit covariance matrix.

        Arguments:
            params (iterable, optional): Iterable of fit parameters to get the covariance for.

        Return:
            `numpy.matrix`: Covariance matrix.

        Raise:
            ValueError: If a requested parameter is not in the fitted parameters list.
            NotInitializedError: If the FitResult has not been initialized.

        """
        if not params:
            params = self.get_fit_parameters().keys()
        params_to_get = [list(self.get_fit_parameters().keys()).index(param) for param in params]
        return self.get_result()['covariance-matrix']['matrix'][np.ix_(params_to_get, params_to_get)]

    @ensure_initialized
    def get_edm(self):
        """Get the fit EDM.

        Return:
            float

        """
        return self._result['edm']

    @ensure_initialized
    def get_min_nll(self):
        """Get the fit Minimum NLL.

        Return:
            float

        """
        return self._result['min_nll']

    @ensure_initialized
    def has_converged(self):
        """Determine whether the fit has converged properly.

        All steps have to have converged and the covariance matrix quality needs to be
        good.

        """
        return not any(status for status in self._result['status'].values()) and \
               self._result['covariance-matrix']['quality'] == 3

    @ensure_initialized
    def get_status_string(self):
        """Get a string summary of the fit status."""
        output = ", ".join("{}: {}".format(step, STATUS[step].get(status, status))
                           for step, status in self._result['status'].items())
        output += ", COVMATRIX: {}".format(COV_CODES[self._result['covariance-matrix']['quality']])
        return output

    @ensure_initialized
    def generate_random_pars(self, params=None, include_const=False):
        """Generate random variation of the fit parameters.

        Use a multivariate Gaussian according to the covariance matrix.

        Arguments:
            params (iterable, optional): Iterable of fit parameters to get. If None is given, all
                parameters are varied.
            include_const (bool, optional): Return constant parameters? Defaults to False. If
                True is given, constant parameters are additionally included independent of `param_list`.

        Return:
            OrderedDict

        """
        if params is None:
            params = self.get_fit_parameters().keys()
        param_values = [self.get_fit_parameter(param_name) for param_name in params]
        # pylint: disable=E1101
        output = OrderedDict(zip(params,
                                 np.random.multivariate_normal([param[0] for param in param_values],
                                                               self.get_covariance_matrix(params))))
        if include_const:
            for name, param in self.get_const_parameters().items():
                output[name] = param
        return output

# EOF
