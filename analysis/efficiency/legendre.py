#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   legendre.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   28.03.2017
# =============================================================================
"""Efficiency expansion with Legendre polynomials."""

import operator
import functools
import itertools

import numpy as np
import pandas as pd

from analysis.utils.logging_color import get_logger

from .efficiency import Efficiency

# Shortcuts
legval = np.polynomial.legendre.legval
legint = np.polynomial.legendre.legint

logger = get_logger('analysis.efficiency.legendre')


###############################################################################
# Utils
###############################################################################
def process_range(range_lst):
    """Process the range, convert to float and manage maths.

    A few functions are allowed: pi, cos, acos, sin, asin, sqrt.

    Returns:
        tuple: Range, (low, high).

    Raises:
        ValueError: If the range doesn't have two elements or if it cannot
        be interpreted.

    """
    # pylint: disable=W0612
    from math import pi, cos, acos, sin, asin, sqrt  # For eval
    try:
        high, low = range_lst
    except ValueError:
        raise ValueError("Wrong number of elements in range")
    try:
        high = float(high)
    except ValueError:  # It's a literal
        try:
            # This is terribly dangerous, but OK...
            # pylint: disable=W0123
            high = float(eval(high))
        except ValueError:
            raise ValueError("Badly formed upper bound")
    try:
        low = float(low)
    except ValueError:  # It's a literal
        try:
            # This is terribly dangerous, but OK...
            # pylint: disable=W0123
            low = float(eval(low))
        except ValueError:
            raise ValueError("Badly formed lower bound")
    return (high, low) if low > high else (low, high)


def scale_dataset(data, input_min, input_max, output_min, output_max):
    """Rescale dataset to put it in the correct range.

    Scaling does (input_min, input_max) -> (output_min, output_max).

    The formula used to go from (input_min, input_max) to (output_min, output_max) is:

            (output_max - output_min)(x - input_min)
     f(x) = ----------------------------------------  + output_min
                      input_max - input_min

    Arguments:
        data (pandas.Series, numpy.array): Data to scale.
        input_min (float): Lower range of the input data.
        input_max (float): Upper range of the input data.
        output_min (float): Lower range of the output data.
        output_max (float): Upper range of the output data.

    Returns:
        pandas.Series, numpy.array: Rescaled dataset.

    """
    if any(data > input_max) or any(data < input_min):
        logger.warning("Scaling a dataset with values outside the range")
    return (output_max-output_min)*(data-input_min)/(input_max-input_min) + output_min


###############################################################################
# Fully correlated Legendre
###############################################################################
class LegendreEfficiency(Efficiency):
    """Implement an efficiency with correlated Legendre functions."""

    MODEL_NAME = 'legendre'

    def __init__(self, var_list, config):
        """Initialize the internal configuration.

        In this case, the configuration of the efficiency model is as follows:
            {'pol-orders':
                {var_name1: n1,
                 var_name2: n2},
             'coefficients': [coeff1, coeff2, ..., coefn1xn2],
             'covariance': [cov1, cov2, ...]
             'ranges': {var_name1: [min_var1, max_var1],
                        var_name2: [min_var2, max_var2]},
             'symmetric-variables': [var_1]}

        The range is used to rescale the data in the `fit` method. If it's not
        given, it's assumed it is [-1, 1].

        Arguments:
            var_list (list): List of observables to apply the efficiency to.
            config (dict): Efficiency model configuration.

        Raises:
            KeyError: On missing coefficients.
            ValueError: On bad range or bad symmetric variable defintion.

        """
        super(LegendreEfficiency, self).__init__(var_list, config)
        self._ranges = {var_name: process_range((low, high))
                        for var_name, (low, high) in config.get('ranges', {}).items()}
        orders = tuple(config['pol-orders'][var] for var in var_list)
        self._coefficients = np.reshape(config['coefficients'], orders)
        self._covariance = np.reshape(config['covariance'],
                                      (functools.reduce(operator.mul, orders),
                                       functools.reduce(operator.mul, orders)))
        for var_name in config.get('symmetric-variables', []):
            logger.debug("Symmetrizing legendre polynomial for variable %s", var_name)
            try:
                index = var_list.index(var_name)
            except ValueError:
                raise ValueError("Symmetrized variable %s is not in the list of variables" % var_name)
            slices = [slice(0, self._coefficients.shape[ind]) for ind in range(index)]
            slices.append(slice(1, self._coefficients.shape[index], 2))
            self._coefficients[tuple(slices)] = 0

    def get_coefficients(self):
        """Get the coefficients in matrix form."""
        return self._coefficients

    def _get_efficiency(self, data, randomize=False):
        """Calculate the efficiency.

        Note:
            No variable checking is performed.

        Arguments:
            data (`pandas.DataFrame`): Data to apply the efficiency to.
            randomize (bool, optional): Apply Gaussian randomization to the efficiencies?
                Defaults to False.

        Returns:
            pandas.Series: Efficiency for each entry of the input.

        """
        for range_var, (min_, max_) in self._ranges.items():
            range_var_name = self.get_variable_names()[range_var]
            data[range_var_name] = scale_dataset(data[range_var_name], min_, max_, -1, 1)
        # Apply polynomial
        if randomize:
            if not np.any(self._covariance):
                raise ValueError("No covariance matrix has been calculated")
            # pylint: disable=E1101
            coeffs = np.random.multivariate_normal(self._coefficients.flatten(),
                                                   self._covariance).reshape(self._coefficients.shape)
        else:
            coeffs = np.array(self._coefficients, copy=True)
        first = True
        for var_name in self.get_variables():
            coeffs = np.polynomial.legendre.legval(data[var_name].values, coeffs, tensor=first)
            first = False
        return pd.Series(coeffs, name="efficiency")

    # pylint: disable=R0914,W0221
    @staticmethod
    def fit(dataset, var_list, weight_var=None, legendre_orders=None, ranges=None, calculate_cov=False, chunk_size=1000):
        """Calculate Legendre coefficients using the method of moments.

        Arguments:
            dataset (pandas.DataFrame): Data to model.
            var_list (list): Variables to model. Defines the order.
            weight_var (str, optional): Variable to use as weight. If `None`
                is given, unity weights are used.
            legendre_orders (dict): Variable name/max Legendre order.
            ranges (dict, optional)
            calculate_cov (bool, optional): Calculate the covariance matrix.
                Defaults to `False`.
            chunk_size (int, optional): Size of the chunks to calculate the
                covariance matrix with. Defaults to 1000.

        Returns:
            `LegendreEfficiency`: Multidimensional efficiency.

        Raises:
            ValueError: If the legendre orders are not given.
            KeyError: If some of the variables or the weight is missing from the
                input dataset.

        """
        if not legendre_orders:
            raise ValueError("Missing parameter -> legendre_orders")
        if ranges is None:
            ranges = {}
        orders = tuple(legendre_orders[var] for var in var_list)
        # Checks
        if not set(var_list).issubset(set(dataset.columns)):
            raise KeyError("Missing variables in the dataset")
        if weight_var and weight_var not in dataset.columns:
            raise KeyError("Missing weight variable in the dataset")
        logger.debug('Copying input data')
        data = dataset[var_list].copy()
        logger.debug('Scaling data')
        for range_var, range_ in ranges.items():
            min_, max_ = process_range(range_)
            data[range_var] = scale_dataset(data[range_var], min_, max_, -1, 1)
        # Loop
        logger.debug('Calculating moments')
        coefficients = np.zeros(orders)
        it_coeffs = np.nditer(coefficients,
                              flags=['multi_index'],
                              op_flags=['readwrite'])
        weights = np.array(dataset[weight_var]) if weight_var else np.ones(dataset.shape[0])
        inv_sum_weights = 1.0/np.sum(weights)
        # Array to store the calculation of the legendres event by event
        events = np.zeros((dataset.shape[0],) + orders)
        while not it_coeffs.finished:
            current_orders = it_coeffs.multi_index
            # Calculate the corresponding legendre for each variable
            legendres = [legval(data[var_name].values,
                                np.array(np.append(np.zeros(current_orders[var_number]), [1])))
                         for var_number, var_name in enumerate(var_list)]
            event = functools.reduce(operator.mul,
                                     ((2.*current_order+1.)/2.
                                      for current_order in current_orders)) * \
                functools.reduce(np.multiply, [weights] + legendres)
            events[(Ellipsis,) + current_orders] = event
            it_coeffs[0] = inv_sum_weights * np.sum(event)
            it_coeffs.iternext()
        logger.debug("Calculating covariance matrix")
        # Flatten
        err_diff_t = (events.reshape(dataset.shape[0], -1) - (weights[np.newaxis].T * coefficients.flatten()))
        err_diff = err_diff_t.T
        if calculate_cov:
            sigma = np.sum(np.dot(err_diff[:, chunk:min(chunk + chunk_size, dataset.shape[0])],
                                  err_diff_t[chunk:min(chunk + chunk_size, dataset.shape[0]), :].conj())
                           for chunk in range(0, dataset.shape[0], chunk_size)) * inv_sum_weights
        else:
            sigma = np.zeros((functools.reduce(operator.mul, orders),
                              functools.reduce(operator.mul, orders)))
        return LegendreEfficiency(var_list, {'pol-orders': legendre_orders,
                                             'coefficients': coefficients.flatten().tolist(),
                                             'covariance': sigma.flatten().tolist(),
                                             'ranges': ranges})

    # pylint: disable=R0914
    def project_efficiency(self, var_name, n_points):
        """Project the efficiency in one variable.

        If multidimensional, the non-projected variables are integrated analytically.

        Arguments:
            var_name (str): Variable to project.
            n_points (int): Number of points of the projection.

        Returns:
            tuple (np.array): x and y coordinates of the projection.

        Raises:
            ValueError: If the requested variable is not modeled by the efficiency object.

        """
        var_pos = self.get_variables().index(var_name)
        x = np.linspace(-1, 1, n_points)
        y = np.zeros(1000)
        coeff_iter = [range(order) for order in self._coefficients.shape]
        for non_int_order in range(self._coefficients.shape[var_pos]):
            coeff_iter[var_pos] = [non_int_order]
            current_coeff = np.zeros(len(self._coefficients.shape), dtype=np.int8)
            current_coeff[var_pos] = non_int_order
            val = 0.0
            for index in itertools.product(*coeff_iter):
                term_val = self._coefficients[index]
                for order_pos, order in enumerate(index):
                    if order_pos == var_pos:
                        continue
                    high, low = legval([1, -1],
                                       legint(np.array(np.append(np.zeros(order), [1])),
                                              lbnd=-1))
                    term_val *= (high-low)
                val += term_val
            y += val * legval(x, np.array(np.append(np.zeros(non_int_order), [1])))
        if var_name in self._ranges:
            x = scale_dataset(x,
                              -1, 1,
                              self._ranges[var_name][0], self._ranges[var_name][1])
            y = y * 2.0 / (self._ranges[var_name][1] - self._ranges[var_name][0])
        return x, y


###############################################################################
# Uncorrelated Legendre
###############################################################################
class LegendreEfficiency1D(Efficiency):
    """Implement an efficiency with uncorrelated Legendre functions."""

    MODEL_NAME = 'legendre1d'

    def __init__(self, var_list, config):
        """Initialize the internal configuration.

        In this case, the configuration of the efficiency model is as follows:
            {'pol-orders':
                {var_name1: n1,
                 var_name2: n2},
             'coefficients': [coeff1, coeff2, ..., coefn1xn2],
             'ranges': {var_name1: [min_var1, max_var1],
                        var_name2: [min_var2, max_var2]},
             'symmetric-variables': [var_1]}

        The range is used to rescale the data in the `fit` method. If it's not
        given, it's assumed it is [-1, 1].

        Arguments:
            var_list (list): List of observables to apply the efficiency to.
            config (dict): Efficiency model configuration.

        Raises:
            KeyError: On missing coefficients or wrong number of them.
            ValueError: On bad range definition.

        """
        super(LegendreEfficiency1D, self).__init__(var_list, config)
        self._ranges = {var_name: process_range((low, high))
                        for var_name, (low, high) in config.get('ranges', {}).items()}
        # Load coefficients
        if len(config['coefficients']) != sum(order for order in config['pol-orders'].values()):
            raise KeyError("Wrong number of coefficients")
        self._coefficients = np.array(np.split(config['coefficients'],
                                               np.cumsum([config['pol-orders'][var_name]
                                                          for var_name in self.get_variables()])[:-1]))
        for var_name in config.get('symmetric-variables', []):
            logger.debug("Symmetrizing legendre polynomial for variable %s", var_name)
            try:
                index = var_list.index(var_name)
            except ValueError:
                raise ValueError("Symmetrized variable %s is not in the list of variables" % var_name)
            slices = [slice(0, self._coefficients.shape[ind]) for ind in range(index)]
            slices.append(slice(0, self._coefficients[index], 2))
            self._coefficients[tuple(slices)] = 0

    def get_coefficients(self):
        """Get the coefficients in list of lists form."""
        return self._coefficients

    def _get_efficiency(self, data):
        """Calculate the efficiency.

        Note:
            No variable checking is performed.

        Arguments:
            data (`pandas.DataFrame`): Data to apply the efficiency to.

        Returns:
            pandas.Series: Efficiency

        """
        for range_var, (min_, max_) in self._ranges.items():
            range_var_name = self.get_variable_names()[range_var]
            data[range_var_name] = scale_dataset(data[range_var_name], min_, max_, -1, 1)
        # Apply polynomials
        effs = np.ones(data.shape[0])
        for var_number, var_name in enumerate(self.get_variables()):
            effs *= np.polynomial.legendre.legval(data[var_name].values, self._coefficients[var_number])
        return pd.Series(effs, name="efficiency")

    # pylint: disable=R0914,W0221
    @staticmethod
    def fit(dataset, var_list, weight_var=None, legendre_orders=None, ranges=None):
        """Calculate Legendre coefficients using the method of moments.

        Arguments:
            dataset (pandas.DataFrame): Data to model.
            var_list (list): Variables to model. Defines the order.
            weight_var (str, optional): Variable to use as weight. If `None`
                is given, unity weights are used.
            legendre_orders (dict): Variable name/max Legendre order.
            ranges (dict, optional)

        Returns:
            `LegendreEfficiency`: Multidimensional efficiency.

        Raises:
            ValueError: If the legendre orders are not given.
            KeyError: If some of the variables or the weight is missing from the
                input dataset.

        """
        if not legendre_orders:
            raise ValueError("Missing parameter -> legendre_orders")
        if ranges is None:
            ranges = {}
        # Checks
        if not set(var_list).issubset(set(dataset.columns)):
            raise KeyError("Missing variables in the dataset")
        if weight_var and weight_var not in dataset.columns:
            raise KeyError("Missing weight variable in the dataset")
        logger.debug('Copying input data')
        data = dataset[var_list].copy()
        logger.debug('Scaling data')
        for range_var, range_ in ranges.items():
            min_, max_ = process_range(range_)
            data[range_var] = scale_dataset(data[range_var], min_, max_, -1, 1)
        # Loop
        weights = np.array(dataset[weight_var]) if weight_var else np.ones(dataset.shape[0])
        inv_sum_weights = 1.0/np.sum(weights)
        coeff_list = []
        for var_name in var_list:
            logger.debug('Calculating moments for %s', var_name)
            coefficients = np.zeros(legendre_orders[var_name])
            for current_order in range(legendre_orders[var_name]):
                coefficients[current_order] = (2.*current_order+1.)/2 * inv_sum_weights * \
                    np.sum(weights *
                           legval(data[var_name].values,
                                  np.array(np.append(np.zeros(current_order), [1]))))
            coeff_list.append(coefficients.tolist())
        return LegendreEfficiency1D(var_list, {'pol-orders': legendre_orders,
                                               'coefficients': sum(coeff_list, []),
                                               'ranges': ranges})

    def project_efficiency(self, var_name, n_points):
        """Project the efficiency in one variable.

        Arguments:
            var_name (str): Variable to project.
            n_points (int): Number of points of the projection.

        Returns:
            tuple (np.array): x and y coordinates of the projection.

        Raises:
            ValueError: If the requested variable is not modeled by the efficiency object.

        """
        var_pos = self.get_variables().index(var_name)
        x = np.linspace(-1, 1, 1000)
        y = legval(x, self._coefficients[var_pos])
        if var_name in self._ranges:
            name = self.get_variable_names()[var_name]
            x = scale_dataset(x,
                              -1, 1,
                              self._ranges[name][0], self._ranges[name][1])
            y = y * 2.0 / (self._ranges[name][1] - self._ranges[name][0])
        return x, y


_EFFICIENCY_MODELS = {'legendre': LegendreEfficiency,
                      'legendre1d': LegendreEfficiency1D}

# EOF
