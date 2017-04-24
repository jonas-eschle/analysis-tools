#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   factory.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   15.04.2017
# =============================================================================
"""Physics factory classes."""

import re
from collections import OrderedDict

import ROOT

from analysis.utils.config import configure_parameter
from analysis.utils.root import execute_and_return_self, list_to_rooargset
from analysis.utils.logging_color import get_logger


logger = get_logger('analysis.physics.factory')


# The base class
class BaseFactory(object):
    """Physics analysis factory.

    Implements the basic skeleton.

    """

    PARAMETERS = None
    MANDATORY_PARAMETERS = {}
    PARAMETER_DEFAULTS = {}

    def __init__(self, config, parameters=None):
        """Initialize the internal object cache.

        Arguments:
            **config (dict): Configuration of the factory.

        Raises:
            KeyError: When parameters are missing.

        """
        if self.PARAMETERS is None and not self.MANDATORY_PARAMETERS:
            logger.warning("Instantiating Factory with no parameters")
        # pylint: disable=C0103
        if self.PARAMETERS is None:
            self.PARAMETERS = list(self.MANDATORY_PARAMETERS)
        self.PARAMETERS = list(self.PARAMETERS)
        # Initialize objects
        self._objects = {}
        self._children = OrderedDict()
        self._config = config
        self._constraints = []
        self._category = None
        # Initialize parameters
        self._parameter_names = {param: param for param in self.PARAMETERS}
        self._parameter_names.update(self._config.get('parameter-names', {}))
        # Set the parameter dictionary
        param_dict = self.PARAMETER_DEFAULTS.copy()
        param_dict.update(config.get('parameters', {}))
        self._constructor_parameters = []
        if parameters:
            self._constructor_parameters = parameters.keys()
            for parameter_name in set(param_dict.keys()) & set(parameters.keys()):
                logger.debug("Skipping parameter %s because it was specified in the constructor", parameter_name)
            param_dict.update(parameters)  # Constructor parameters have priority
        # Now, build parameters
        missing_parameters = []
        for parameter_name in self.PARAMETERS:
            if parameter_name not in param_dict:
                missing_parameters.append(parameter_name)
                continue
            parameter_value = param_dict.pop(parameter_name)
            parameter, constraint = self._create_parameter(parameter_name, parameter_value)
            if constraint:
                self._constraints.append(constraint)
            self.set(parameter_name, parameter)
        if missing_parameters:
            if 'Yield' in missing_parameters:
                logger.debug("Initial yield not specified")  # Most of the time you won't want to do it
            raise KeyError("Missing parameters -> %s" % ','.join(missing_parameter
                                                                 for missing_parameter in missing_parameters))
        if 'Yield' in param_dict:
            yield_value = param_dict.pop('Yield')
            yield_, constraint = self._create_parameter('Yield', yield_value)
            if constraint:
                self._constraints.append(constraint)
            self.set('Yield', yield_)
        if param_dict:
            logger.warning("Trying to set unsupported params in config. I skipped them -> %s",
                           ','.join(param_dict.keys()))

    def get_config(self):
        return self._config

    def get_children(self):
        return self._children

    def get_constraints(self):
        return list_to_rooargset(self._constraints + [constraint
                                                      for child in self.get_children()
                                                      for constraint in child.get_constraints()])

    def _find_object(self, name):
        """Find object here or in children. Priority is here."""
        if name in self._objects:
            return self._objects[name]
        for child in self._children.values():
            if name in child:
                return child[name]
        return None

    def get(self, key, init_val=None, recursive=True):
        """Get object from the ROOT workspace.

        If the object is not there and `init_val` is given, it is added
        and returned.

        We look in children too.

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
        if recursive:
            obj = self._find_object(key)
        else:
            obj = self._objects.get(key, None)
        if not obj:
            if init_val is not None:
                self._objects[key] = init_val
            return self._objects[key]
        return obj

    def __getitem__(self, key):
        """Get object from internal ROOT workspace.

        Arguments:
            key (str): Object identifier.

        Returns:
            object: Object in the workspace.

        Raises:
            KeyError: if `key` is not in the internal workspace.

        """
        obj = self._find_object(key)
        if not obj:
            raise KeyError("Cannot find %s in object" % key)
        return obj

    def set(self, key, object_):
        """Set an object in the internal ROOT workspace.

        Arguments:
            key (str): Object identifier.
            object_ (object): Object to store.

        Returns:
            object: The object.

        """
        self._objects[key] = object_
        return self[key]

    def __setitem__(self, key, object_):
        """Get object from internal ROOT workspace.

        Arguments:
            key (str): Object identifier.
            object_ (object): Object to store.

        """
        self._objects[key] = object_

    def __contains__(self, key):
        """Check if an object is in the internal ROOT workspace.

        Arguments:
            key (str): Object identifier.

        Returns:
            bool: Wether the object is in the workspace.

        """
        return self._find_object(key) is not None

    def _create_parameter(self, parameter_name, parameter_value):
        if isinstance(parameter_value, ROOT.TObject):  # It's a string specification
            self._parameter_names[parameter_name] = parameter_value.GetName()
            constraint = None
        else:
            var = ROOT.RooRealVar(self.get_parameter_name(parameter_name),
                                  self.get_parameter_name(parameter_name),
                                  0.0)
            constraint = configure_parameter(var, parameter_value)
            parameter_value = var
        return execute_and_return_self(parameter_value,
                                       'setStringAttribute',
                                       'originalName',
                                       parameter_name), constraint

    def get_parameter_name(self, param_id):
        """Get the name of the parameter according to the configuration.

        Defaults to the same name if no parameter naming has been given.

        """
        return self._parameter_names.get(param_id, param_id)

    def set_parameter_names(self, name_dict):
        """Set parameter name conversion.

        Arguments:
            name_dict (dict): (name -> new name) pairs.

        Returns:
            bool: True only if all requested renaming operations have been
                performed.

        Raises:
            KeyError: If some of the parameter names is unknown.

        """
        if not set(name_dict.keys()).issubset(set(self.PARAMETERS + ['Yield'])):
            raise KeyError("Bad renaming scheme!")
        all_good = True
        # logger.debug("Requesting a parameter name change -> %s", name_dict)
        for base_name, new_name in name_dict.items():
            if base_name in self._constructor_parameters:
                all_good = False
                continue
            # Now rename the parameters if necessary
            if base_name in self._objects:
                self._objects[base_name].SetName(new_name)
                self._objects[base_name].SetTitle(new_name)
            self._parameter_names[base_name] = new_name
        return all_good

    def _add_superscript(self, name, superscript, old_first=True):
        subscript_match = re.search(r'\^{(.*?)}', name)
        sub_func = lambda match, name=superscript: '^{%s,%s}' % (match.groups()[0], name) \
            if old_first \
            else lambda match, name=superscript: '^{%s,%s}' % (name, match.groups()[0])
        if subscript_match:
            new_name = re.sub(r'\^{(.*?)}',
                              sub_func,
                              name)
        else:
            new_name = '%s^{%s}' % (name, superscript)
        return new_name

    def rename_children_parameters(self, naming=None):
        if not naming:
            naming = self._children.viewitems()
        naming = list(naming)
        for label, factory in naming:
            # Recursively rename children
            if factory.get_children():
                factory.rename_children_parameters(('%s,%s' % (label, child_name), child)
                                                   for child_name, child in factory.get_children().items())
            parameters_to_set = {}
            for param_id in factory.PARAMETERS + ['Yield']:
                parameters_to_set[param_id] = self._add_superscript(factory.get_parameter_name(param_id),
                                                                    label)
            factory.set_parameter_names(parameters_to_set)

    def get_pdf(self, name, title):
        """Get the physics PDF.

        Raises:
            NotImplementedError

        """
        pdf_name = 'pdf_%s' % name
        return self.get(pdf_name) \
            if pdf_name in self \
            else self.set(pdf_name, self.get_unbound_pdf(name, title))

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Raises:
            NotImplementedError

        """
        raise NotImplementedError()

    def get_extended_pdf(self, name, title, yield_val=None, yield_name=None):
        """Get an extended physics PDF.

        Returns:
            `ROOT.RooExtendPdf`.

        Raises:
            ValueError: If the yield had not been configured previously

        """
        raise NotImplementedError()

    def get_observables(self):
        """Get the physics observables.

        Raises:
            NotImplementedError

        """
        raise NotImplementedError()

    def get_fit_parameters(self, extended=False):
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
        raise NotImplementedError()

    def get_yield_var(self):
        return self.get('Yield', None)

    def get_category_var(self):
        return self._category

    def is_simultaneous(self):
        return self._category is not None

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

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Raises:
            NotImplementedError

        """
        raise NotImplementedError()

    def get_extended_pdf(self, name, title, yield_val=None, yield_name=None):
        """Get an extended physics PDF.

        Returns:
            `ROOT.RooExtendPdf`.

        Raises:
            ValueError: If the yield had not been configured previously

        """
        # Configure yield
        if 'Yield' not in self._objects:
            if yield_val is None:
                raise ValueError("Initial yield not configured -> %s" % self)
            if yield_name:
                self._parameter_names['Yield'] = yield_name
            yield_param, yield_constraint = self._create_parameter('Yield', yield_val)
            if yield_constraint:
                self._constraints.append(yield_constraint)
            self.set('Yield', yield_param)
        # Return the extended PDF
        pdf_name = 'pdf_%s' % name
        return self.get(pdf_name) \
            if pdf_name in self \
            else self.set(pdf_name, ROOT.RooExtendPdf(name,
                                                      title,
                                                      self.get_pdf(name+'_{noext}', title+'_{noext}'),
                                                      self.get('Yield')))

    def get_observables(self):
        """Get the physics observables.

        Raises:
            NotImplementedError

        """
        raise NotImplementedError()

    def get_fit_parameters(self, extended=False):
        """Get the PDF fit parameters.

        Returns:
            tuple[`ROOT.RooRealVar`]: Parameters as defined by the `PARAMETERS` attribute.

        """
        params = self.PARAMETERS[:]
        if extended and 'Yield' in self:
            params.append('Yield')
        return tuple(self.get(param_name) for param_name in params)

    def get_gen_parameters(self):
        """Get all the necessary generation parameters.

        Returns the fit parameters by default.

        Returns:
            tuple[`ROOT.RooRealVar`]

        """
        return self.get_fit_parameters()


# Product Physics Factory
class ProductPhysicsFactory(BaseFactory):
    """RooProdPdf of different observables."""

    PARAMETERS = []  # No extra parameters here

    def __init__(self, factories, parameters=None):
        """Initialize.

        In this case, the children are a map of observable -> Factory.

        """
        super(ProductPhysicsFactory, self).__init__({}, parameters)
        # Rename action -> Add the observable in the superscript of each variable
        self._children = factories

    def get_unbound_pdf(self, name, title):
        """Get unbound PDF."""
        pdfs = ROOT.RooArgList()
        for observable, factory in self._children.items():
            new_name = self._add_superscript(name, observable)
            pdfs.add(factory.get_pdf(new_name, new_name))
        return ROOT.RooProdPdf(name, title, pdfs)

    def get_extended_pdf(self, name, title, yield_val=None, yield_name=None):
        """Get an extended physics PDF.

        Returns:
            `ROOT.RooExtendPdf`.

        Raises:
            ValueError: If the yield had not been configured previously

        """
        # Configure yield
        if 'Yield' not in self._objects:
            if yield_val is None:
                raise ValueError("Initial yield not configured")
            if yield_name:
                self._parameter_names['Yield'] = yield_name
            yield_param, yield_constraint = self._create_parameter('Yield', yield_val)
            if yield_constraint:
                self._constraints.append(yield_constraint)
            self.set('Yield', yield_param)
        # Return the extended PDF
        return self.get(name) \
            if name in self \
            else self.set(name, ROOT.RooExtendPdf(name,
                                                  title,
                                                  self.get_pdf(name+'_{noext}', title+'_{noext}'),
                                                  self.get('Yield')))

    def get_observables(self):
        """Get the physics observables.

        Returns:
            tuple: Observables in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        return tuple(obs
                     for factory in self._children.values()
                     for obs in factory.get_observables())

    def get_gen_parameters(self):
        """Get the PDF generation parameters.

        Returns:
            tuple: Generation parameters in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        return tuple(param
                     for factory in self._children.values()
                     for param in factory.get_gen_parameters())

    def get_fit_parameters(self, extended=False):
        """Get the PDF fit parameters.

        Returns:
            tuple: Fit parameters in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        return tuple(param
                     for factory in self._children.values()
                     for param in factory.get_fit_parameters(extended))

    def transform_dataset(self, dataset):
        """Transform dataset according to the factory configuration.

        The transformations of the children are applied in sequence.

        Arguments:
            dataset (pandas.DataFrame): Data frame to fold.

        Returns:
            `pandas.DataFrame`: Input dataset with the transformation applied.

        """
        for factory in self._children.values():
            dataset = factory.transform_dataset(dataset)
        return dataset


# Sum physics factory
class SumPhysicsFactory(BaseFactory):
    """RooProdPdf of different observables."""

    PARAMETERS = []  # No extra parameters here

    def __init__(self, factories):
        """Initialize.

        In this case, the children are a map of PDF name -> Factory.

        Raises:
            ValueError: When the observables of the factories are

        """
        # Check observable compatibility
        if len({tuple([obs.GetName() for obs in factory.get_observables()])
                for factory in factories.values()}) != 1:
            raise ValueError("Incompatible observables")
        super(SumPhysicsFactory, self).__init__({}, None)
        # Rename action -> Add the observable in the superscript of each variable
        self._children = factories

    def get_unbound_pdf(self, name, title):
        logger.warning("All RooAddPdfs are Extended. "
                       "An extended PDF will be returned even if a non-extended one has been requested.")
        return self.get_extended_pdf(name, title)

    def get_extended_pdf(self, name, title, yield_val=None, yield_name=None):
        if yield_val is not None:
            logger.warning("Specified yield for a RooAddPdf. "
                           "Since the yield is defined by its children, I'm ignoring it.")
        if yield_name is not None:
            logger.warning("Specified yield name for a RooAddPdf. "
                           "Since the yield name is defined by its children, I'm ignoring it.")
        pdf_name = 'pdf_%s' % name
        if pdf_name in self:
            return self.get(pdf_name)
        else:
            pdfs = ROOT.RooArgList()
            for child_name, child in self._children.items():
                new_name = self._add_superscript(name, child_name)
                pdfs.add(child.get_extended_pdf(new_name, new_name))
            return self.set(pdf_name, ROOT.RooAddPdf(name, title, pdfs))

    def get_observables(self):
        """Get the physics observables.

        Returns:
            tuple: Observables in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        return self._children.values()[0].get_observables()

    def get_gen_parameters(self):
        """Get the PDF generation parameters.

        Returns:
            tuple: Generation parameters in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        return tuple(param
                     for factory in self._children.values()
                     for param in factory.get_gen_parameters())

    def get_fit_parameters(self, extended=False):
        """Get the PDF fit parameters.

        Returns:
            tuple: Fit parameters in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        return tuple(param
                     for factory in self._children.values()
                     for param in factory.get_fit_parameters(extended))

    def transform_dataset(self, dataset):
        """Transform dataset according to the factory configuration.

        Since all PDFs of the addition are supposed to need the same transformation,
        the dataset is transformed according to the first one

        Arguments:
            dataset (pandas.DataFrame): Data frame to fold.

        Returns:
            `pandas.DataFrame`: Input dataset with the transformation applied.

        """
        return self._children.values()[0](dataset)


# Sum physics factory
class SimultaneousPhysicsFactory(BaseFactory):
    """Simultaneous fit factory."""

    PARAMETERS = []

    def __init__(self, factories, category_var):
        """Initialize.

        The category var has the types already defined. `factories` keys are tuples
        in the categories (or a string if there's only one)

        """
        # Check observable compatibility
        super(SimultaneousPhysicsFactory, self).__init__({}, None)
        self._category = category_var
        self._children = {';'.join(label): factory
                          for label, factory in factories.items()}

    def get_unbound_pdf(self, name, title):
        sim_pdf = ROOT.RooSimultaneous(name, title, self._category)
        for category, child in self._children.items():
            new_name = self._add_superscript(name, category)
            sim_pdf.addPdf(child.get_extended_pdf(new_name,
                                                  new_name),
                           '{%s}' % category if category.count(';') > 0 else category)
        return sim_pdf

    def get_extended_pdf(self, name, title, yield_val=None, yield_name=None):
        logger.warning("The concept of extended RooSimultaneous is not implemented. "
                       "A RooSimultaneous PDF will be returned even if an extended one has been requested.")
        return self.get_unbound_pdf(name, title)

    def get_observables(self):
        """Get the physics observables.

        Returns:
            tuple: Observables in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        obs_list = OrderedDict()
        for child in self._children.values():
            for child_obs in child.get_observables():
                if child_obs.GetName() not in self._objects:
                    obs_list[child_obs.GetName()] = self.set(child_obs.GetName(), child_obs)
                elif child_obs.GetName() not in obs_list:
                    obs_list[child_obs.GetName()] = self.get(child_obs.GetName())
        return tuple(obs_list.values())

    def get_gen_parameters(self):
        """Get the PDF generation parameters.

        Returns:
            tuple: Generation parameters in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        return tuple(param
                     for factory in self._children.values()
                     for param in factory.get_gen_parameters())

    def get_fit_parameters(self, extended=False):
        """Get the PDF fit parameters.

        Returns:
            tuple: Fit parameters in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        return tuple(param
                     for factory in self._children.values()
                     for param in factory.get_fit_parameters(extended))

    def transform_dataset(self, dataset):
        """Transform dataset according to the factory configuration.

        The category nane is used as column name to determine each of the
        samples to transform.

        Arguments:
            dataset (pandas.DataFrame): Data frame to fold.

        Returns:
            `pandas.DataFrame`: Input dataset with the transformation applied.

        Raises:
            ValueError: When the dataset contains categories that have not been configured
                in the class.

        """
        cat_var = self._category.GetName()
        categories = dataset.groupby(cat_var).indices.keys()
        # A simple check
        if not set(categories).issubset(set(self._children.keys())):
            raise ValueError("Dataset contains categories not defined in the SimultaneousPhysicsFactory")
        for category in categories:
            dataset[cat_var == category] = self._children[category].transform_dataset([cat_var == category])
        return dataset

# EOF
