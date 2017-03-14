#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   factory.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   18.01.2017
# =============================================================================
"""Base Physics factory clases."""

from functools import partial

import ROOT

from analysis.utils.root import execute_and_return_self
from .helpers import build_factory_prod, bind_to_object


# The base class
class BaseFactory(object):
    """Physics analysis factory.

    Implements the basic skeleton.

    """

    PARAMETERS = None

    def __init__(self, **config):
        """Initialize the internal ROOT workspace.

        Arguments:
            **config (dict): Configuration of the factory.

        """
        self._ws = {}
        self._config = config
        self._parameter_names = {}
        self._parameter_values = getattr(self, 'PARAMETER_DEFAULTS', {})

    def get(self, key, init_val=None):
        """Get object from the ROOT workspace.

        If the object is not there and `init_val` is given, it is added
        and returned.

        Arguments:
            key (str): Object identifier.
            init_val (object): Object to add to the workspace if the key is not
                present in the workspace.

        Returns:
            object: Object in the workspace.

        Raises:
            KeyError: if `key` is not in the internal workspace and no `init_val`
                is given.

        """
        if key not in self._ws and init_val is not None:
            self._ws[key] = init_val
        return self[key]

    def __getitem__(self, key):
        """Get object from internal ROOT workspace.

        Arguments:
            key (str): Object identifier.

        Returns:
            object: Object in the workspace.

        Raises:
            KeyError: if `key` is not in the internal workspace.

        """
        return self._ws[key]

    def __contains__(self, key):
        """Check if an object is in the internal ROOT workspace.

        Arguments:
            key (str): Object identifier.

        Returns:
            bool: Wether the object is in the workspace.

        """
        return key in self._ws

    def _get_obj_name(self, name):
        """Get the name of the parameter according to the configuration.

        Defaults to the same name if no parameter naming has been given

        """
        return self._parameter_names.get(name, name)

    def _get_roorealvar(self, param_name, val=None, min_val=None, max_val=None):
        """Get a fit parameter.

        If it doesn't exist, create a new RooRealVar taking into account possible
        name transformations, otherwise get it from the internal workspace. Additionally,
        the variable is set to non-constant and its 'originalName' attribute is set
        to the given parameter name (without transformations).

        Arguments:
            param_name (str): Parameter name, as defined by the factory.
            val (float, optional): Initialization value for the parameter. If not given,
                the config value will be used.
            min_val (float, optional): Lower range for the variable.
            max_val (float, optional): Upper range for the variable. Only of `max_val` and
                `min_val` are given, the range is set.

        Returns:
            ROOT.RooRealVar.

        Raises:
            KeyError: If there is no initial value for the variable.

        """
        value = val if val is not None else self._parameter_values[param_name]
        limits = [min_val, max_val] if min_val and max_val else []
        return self.get(param_name,
                        execute_and_return_self(
                            execute_and_return_self(ROOT.RooRealVar(self._get_obj_name(param_name),
                                                                    self._get_obj_name(param_name),
                                                                    value,
                                                                    *limits),
                                                    'setStringAttribute',
                                                    'originalName',
                                                    param_name),
                            'setConstant',
                            False))

    def get_pdf(self):
        """Get the physics PDF.

        Raises:
            NotImplementedError

        """
        raise NotImplementedError()

    def get_extended_pdf(self):
        """Get an extended physics PDF.

        Returns:
            `ROOT.RooExtendPdf`.

        """
        return bind_to_object(self)(partial(lambda self, name, title, yield_name, yield_val=None, *inputs:
                                            ROOT.RooExtendPdf(name,
                                                              title,
                                                              self.get_pdf()(name+'_{noext}',
                                                                             title+'_{noext}',
                                                                             *inputs),
                                                              execute_and_return_self(
                                                                  execute_and_return_self(
                                                                      self._get_roorealvar('N', yield_val),
                                                                      'SetTitle',
                                                                      yield_name),
                                                                  'SetName',
                                                                  yield_name)),
                                            self))

    def get_observables(self):
        """Get the physics observables.

        Raises:
            NotImplementedError

        """
        raise NotImplementedError()

    def get_fit_parameters(self):
        """Get the PDF fit parameters.

        Raises:
            NotImplementedError

        """
        raise NotImplementedError()

    def get_gen_parameters(self):
        """Get all the necessary generation parameters.

        Returns the fit parameters by default.

        Returns:
            tuple[`ROOT.RooRealVar`]

        """
        return self.get_fit_parameters()

    # pylint: disable=R0201
    def transform_dataset(self, dataset):
        """Transform dataset according to the factory configuration.

        Note:
            It's recommended to pass a copy since the dataset is modified
            in place.

        Arguments:
            dataset (pandas.DataFrame): Data frame to fold.

        Returns:
            `pandas.DataFrame`: Input dataset with the transformation applied.

        """
        return dataset


# Single model Factory
class PhysicsFactory(BaseFactory):
    """Physics analysis factory.

    Implements the basic skeleton for single models.

    """

    def __init__(self, **config):
        """Initialize the internal ROOT workspace and parameter values.

        The 'parameters' keyword is extracted from the configuration to
        obtain the starting values for the fit parameters. If the class
        provides a `PARAMETER_DEFAULTS` attribute, it's also used for those
        parameters not included in the 'parameters' configuration. If a
        class provides a `MANDATORY_PARAMETERS` attribute, it is checked that
        it exists, either in the configuration or as a default value.

        In any case, the list of parameters must be given in the `PARAMETERS`
        attribute.

        Additionally, parameters can be renamed by giving the 'parameter-names'
        configuration.

        Arguments:
            **config (dict): Configuration of the factory.

        """
        try:
            assert self.PARAMETERS is not None
        except AssertionError:
            import ipdb
            ipdb.set_trace()
        super(PhysicsFactory, self).__init__(**config)
        # pylint: disable=E1101
        if hasattr(self, 'MANDATORY_PARAMETERS'):
            for parameter in self.MANDATORY_PARAMETERS:
                if parameter not in config.get('parameters', {}) and\
                        parameter not in self._parameter_values:
                    raise MissingParameter("Missing parameter -> %s" % parameter)
        self._parameter_values.update(self._config.pop('parameters', {}))
        self._parameter_names.update(self._config.pop('parameter-names', {}))
        self._name = self._config.pop('name', None)
        self._type = self._config.pop('type')
        self._observables = self._config.pop('observables')

    def set_parameter_names(self, name_dict):
        """Set parameter name conversion.

        Arguments:
            name_dict (dict): (name -> new name) pairs.

        Raises:
            KeyError: If some of the parameter names is unknown.

        """
        if not set(name_dict.keys()).issubset(set(self.PARAMETERS)):
            raise KeyError("Bad renaming scheme!")
        self._parameter_names = name_dict
        # Now rename the parameters if necessary
        for parameter_name in self._parameter_names:
            if parameter_name in self._ws:
                self._ws[parameter_name].SetName(self._parameter_names[parameter_name])
                self._ws[parameter_name].SetTitle(self._parameter_names[parameter_name])

    def get_pdf(self):
        """Get the physics PDF.

        Raises:
            NotImplementedError

        """
        raise NotImplementedError()

    def get_observables(self):
        """Get the physics observables.

        Raises:
            NotImplementedError

        """
        raise NotImplementedError()

    def get_fit_parameters(self):
        """Get the PDF fit parameters.

        Returns:
            tuple[`ROOT.RooRealVar`]: Parameters as defined by the `PARAMETERS` attribute.

        """
        return tuple(self._get_roorealvar(param_name)
                     for param_name in self.PARAMETERS)


class ProductPhysicsFactory(BaseFactory):
    """Product of several physics factories with different observables."""

    def __init__(self, factories):
        """Check the compatibility of the factories.

        Note:
            Order matters in terms of order of observables.

        Arguments:
            factories (list[`PhysicsFactory`]): Physics factories to merge.

        Raises:
            KeyError: If there are shared observables.

        """
        if set.intersection(*[{factory.TYPE} for factory in factories]):
            raise KeyError("Shared observables!")
        super(ProductPhysicsFactory, self).__init__()
        self._factory_classes = factories
        self._factories = None

    def __call__(self, config):
        """Initialize the factories.

        Mimics the class instantiation and instantiates the internal factories.

        Arguments:
            config (list): Configuration of the factories.

        Raises:
            ValueError: If the number of pdfs in `config` doesn't match what was given
                on initialization.
            KeyError: If there are duplicate parameter names.

        """
        if len(config) != len(self._factory_classes):
            ValueError("Wrong number of classes given.")
        # Instantiate the classes
        self._factories = [Factory(**config[class_num])
                           for class_num, Factory in enumerate(self._factory_classes)]
        # pylint: disable=C0103
        self.PARAMETERS = tuple(parameter
                                for factory in self._factories
                                for parameter in factory.PARAMETERS)
        if len(self.PARAMETERS) != len(set(self.PARAMETERS)):  # Parameter names are repeated
            raise KeyError("Duplicate parameter name")
        return self

    def set_parameter_names(self, name_dict):
        """Set parameter name conversion.

        Arguments:
            name_dict (dict): (name -> new name) pairs.

        Raises:
            KeyError: If some of the parameter names is unknown.

        """
        for factory in self._factories:
            factory.set_parameter_names({param_name: name_dict[param_name]
                                         for param_name in factory.PARAMETERS
                                         if param_name in name_dict})

    def get_pdf(self):
        """Get the physics PDF.

        The returned object behaves like a `RooAbsPdf` class in the sense that
        it can be called, similarly to a `RooAbsPdf`, and the returned object
        is a `RooProdPdf.`

        Returns:
            `ProdPDF`: PDF-like object that simulates a `RooAbsPdf` class.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        if not self._factories:
            raise NotInitializedError()
        return bind_to_object(self)(build_factory_prod(self._factories))

    def get_observables(self):
        """Get the physics observables.

        Returns:
            tuple: Observables in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        if not self._factories:
            raise NotInitializedError()
        return tuple(obs
                     for factory in self._factories
                     for obs in factory.get_observables())

    def get_gen_parameters(self):
        """Get the PDF generation parameters.

        Returns:
            tuple: Generation parameters in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        if not self._factories:
            raise NotInitializedError()
        return tuple(param
                     for factory in self._factories
                     for param in factory.get_gen_parameters())

    def get_fit_parameters(self):
        """Get the PDF fit parameters.

        Returns:
            tuple: Fit parameters in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        if not self._factories:
            raise NotInitializedError()
        return tuple(param
                     for factory in self._factories
                     for param in factory.get_fit_parameters())

    # pylint: disable=R0201
    def transform_dataset(self, dataset):
        """Transform dataset according to the factory configuration.

        Transformation for all factories is applied in sequence.

        Note:
            It's recommended to pass a copy since the dataset is modified
            in place.

        Arguments:
            dataset (pandas.DataFrame): Data frame to fold.

        Returns:
            `pandas.DataFrame`: Input dataset with the transformation applied.

        """
        for factory in self._factories:
            dataset = factory.transform_dataset(dataset)
        return dataset


class NotInitializedError(Exception):
    """Exception for not initialized."""


class MissingParameter(Exception):
    """Exception for missing mandatory parameter."""

# EOF
