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
from analysis.utils.root import execute_and_return_self, list_to_rooargset, list_to_rooarglist
from analysis.utils.logging_color import get_logger


logger = get_logger('analysis.physics.factory')


# The base class
class BaseFactory(object):
    """Physics analysis factory.

    Implements the basic skeleton.

    """

    OBSERVABLES = OrderedDict()
    PARAMETERS = None
    MANDATORY_PARAMETERS = {}
    PARAMETER_DEFAULTS = OrderedDict()

    def __init__(self, config, parameters=None):
        """Initialize the internal object cache.

        Arguments:
            **config (dict): Configuration of the factory.

        Raises:
            KeyError: When parameters or observables are missingo or there is an
                inconsistency in the configuration.

        """
        # pylint: disable=C0103
        if not isinstance(self.OBSERVABLES, OrderedDict):
            self.OBSERVABLES = OrderedDict((obs[0], obs) for obs in self.OBSERVABLES)
        if self.PARAMETERS is None:
            if not self.MANDATORY_PARAMETERS:
                logger.warning("Instantiating Factory with no parameters")
            else:
                self.PARAMETERS = list(self.MANDATORY_PARAMETERS)
        self.PARAMETERS = list(self.PARAMETERS)
        # Initialize objects
        self._objects = {}
        self._children = OrderedDict()
        self._config = config
        self._constraints = set() if parameters is None else set(parameters.get('constraints', []))
        self._category = None
        # Initialize parameters
        self._parameter_names = {param: param for param in self.PARAMETERS}
        self._parameter_names.update(self._config.get('parameter-names', {}))
        # Update observable names
        for obs_name, new_obs_name in self._config.get('observable-names', {}).items():
            self.set_observable(obs_name, name=new_obs_name)
        # Set the parameter dictionary
        param_dict = self.PARAMETER_DEFAULTS.copy()
        param_dict.update(config.get('parameters', OrderedDict()))
        if parameters:
            # First parameters
            params = parameters.pop('parameters', {})
            for parameter_name in set(param_dict.keys()) & set(params.keys()):
                logger.debug("Skipping parameter %s because it was specified in the constructor", parameter_name)
            for param_name, (param, constraint) in params.items():
                param_dict[param_name] = param  # Constructor parameters have priority
                if constraint:
                    self._constraints.add(constraint)
        # Now, build parameters
        missing_parameters = []
        for parameter_name in self.PARAMETERS:
            if parameter_name not in param_dict:
                missing_parameters.append(parameter_name)
                continue
            self._create_parameter(parameter_name,
                                   param_dict.pop(parameter_name),
                                   {key.split('/')[-1]: val for key, val in param_dict.items()})
        if missing_parameters:
            raise KeyError("Missing parameters -> {}".format(','.join(missing_parameter
                                                                      for missing_parameter in
                                                                      missing_parameters)))
        if param_dict:
            logger.debug("Trying to set unsupported params in config. I stored them but they can cause problems -> %s",
                         ','.join(param_dict.keys()))
            for param_name, param_val in param_dict.items():
                self._create_parameter(param_name, param_val)

    def get_config(self):
        return self._config

    def get_children(self):
        return self._children

    def get_constraints(self):
        child_constraints = list_to_rooargset(self._constraints)
        for child in self.get_children().values():
            tmp_constraints = child.get_constraints()
            if tmp_constraints:
                child_constraints = ROOT.RooArgSet(child_constraints, child.get_constraints())
        return child_constraints

    def _find_object(self, name):
        """Find object here or in children. Priority is here."""
        if name in self._objects:
            return self._objects[name]
        for child in self._children.values():
            if name in child:
                return child[name]
        return None

    def get(self, key, default=None, recursive=False):
        """Get object from the ROOT workspace.

        If the object is not there and `default` is given, it is added
        and returned.

        We look in children too.

        Arguments:
            key (str): Object identifier.
            default (any): The value to return if *key* is not found. Default is None.
            recursive (bool): If True, the object is searched recursively
            including its children with a stop-if-found rule.

        Returns:
            object: Object in the workspace.

        Raises:
            KeyError: if `key` is not in the internal workspace and no `default`
                is given.

        """
        if recursive:
            obj = self._find_object(key)
        else:
            obj = self._objects.get(key, None)
        return obj if obj else default

    def __getitem__(self, key):
        """Get object from internal ROOT workspace.

        Arguments:
            key (str): Object identifier.

        Returns:
            object: Object in the workspace.

        Raises:
            KeyError: if `key` is not in the internal workspace.

        """
        return self._objects[key]

    def set(self, key, object_, overwrite=False):
        """Set an object in the internal ROOT workspace.

        Arguments:
            key (str): Object identifier.
            object_ (object): Object to store.
            overwrite (bool, optional): Replace the existing object?
                Defaults to False.

        Returns:
            object: The object.

        """
        if overwrite or key not in self._objects:
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
        return key in self._objects

    def _create_parameter(self, parameter_name, parameter_value, external_vars=None):
        if parameter_name in self._objects:
            return self._objects[parameter_name]
        if isinstance(parameter_value, (tuple, list)):  # It's a parameter with a constraint
            parameter_value, constraint = parameter_value
        elif isinstance(parameter_value, ROOT.TObject):  # It's an already built parameter
            if parameter_value.getStringAttribute('tempName') == 'true':
                parameter_value.SetName(self.get_parameter_name(parameter_name))
                parameter_value.SetTitle(self.get_parameter_name(parameter_name))
                parameter_value.setStringAttribute('tempName', '')
            else:
                self._parameter_names[parameter_name] = parameter_value.GetName()
            constraint = None
        else:  # String specification
            parameter_value, constraint = configure_parameter(self.get_parameter_name(parameter_name),
                                                              self.get_parameter_name(parameter_name),
                                                              parameter_value,
                                                              external_vars)
        if constraint:
            self._constraints.add(constraint)
        return self.set(parameter_name,
                        execute_and_return_self(parameter_value,
                                                'setStringAttribute',
                                                'originalName',
                                                parameter_name))

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
            KeyError: If some of the parameter names are unknown.

        """
        if not set(name_dict.keys()).issubset(set(self.PARAMETERS + ['Yield', 'Fraction'])):
            raise KeyError("Bad renaming scheme!")
        all_good = True
        logger.debug("Requesting a parameter name change -> %s", name_dict)
        for base_name, new_name in name_dict.items():
            if base_name in self._objects:
                if self._objects[base_name].getStringAttribute('shared') == 'true':
                    all_good = False
                    continue
                self._objects[base_name].SetName(new_name)
                self._objects[base_name].SetTitle(new_name)
            self._parameter_names[base_name] = new_name
        return all_good

    def _add_superscript(self, name, superscript, old_first=True):
        subscript_match = re.search(r'\^{(.*?)}', name)
        sub_func = lambda match, name=superscript: '^{{{},{}}}'.format(match.groups()[0], name) \
            if old_first \
            else lambda match, name=superscript: '^{{{},{}}}'.format(name, match.groups()[0])
        if subscript_match:
            new_name = re.sub(r'\^{(.*?)}',
                              sub_func,
                              name)
        else:
            new_name = '{}^{{{}}}'.format(name, superscript)
        return new_name

    def rename_children_parameters(self, naming_scheme=None):
        if not naming_scheme:
            naming_scheme = self._children.viewitems()
        for label, factory in list(naming_scheme):
            # Recursively rename children
            factory.rename_children_parameters(('{},{}'.format(label, child_name), child)
                                               for child_name, child in factory.get_children().items())
            parameters_to_set = {}
            for param_id in factory.PARAMETERS + ['Yield', 'Fraction']:
                parameters_to_set[param_id] = self._add_superscript(factory.get_parameter_name(param_id),
                                                                    label)
            factory.set_parameter_names(parameters_to_set)

    def get_pdf(self, name, title):
        """Get the physics PDF.

        Raises:
            NotImplementedError

        """
        if self.has_to_be_extended():
            raise ValueError("Requested non-extended PDF, "
                             "but the factory needs to be extended")
        pdf_name = 'pdf_{}'.format(name)
        return self.get(pdf_name) \
            if pdf_name in self \
            else self.set(pdf_name, self.get_unbound_pdf(name, title))

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Raises:
            NotImplementedError

        """
        raise NotImplementedError()

    def get_extended_pdf(self, name, title, yield_val=None):
        """Get an extended physics PDF.

        Returns:
            `ROOT.RooExtendPdf`.

        Raises:
            ValueError: If the yield had not been configured previously

        """
        # Configure yield
        if not self.is_extended():
            if yield_val is None:
                raise ValueError("Yield value not given -> {}".format(self))
            self.set_yield_var(yield_val)
        elif yield_val is not None:
            logger.warning("Specified yield value but it's already defined. Ignoring.")
        # Avoid name clashes
        pdf_name = 'pdfext_{}'.format(name)
        return self.get(pdf_name) \
            if pdf_name in self \
            else self.set(pdf_name, self.get_unbound_extended_pdf(name, title))

    def get_unbound_extended_pdf(self, name, title):
        """Get an extedned physics PDF."""
        raise NotImplementedError()

    def is_extended(self):
        return 'Yield' in self

    def has_to_be_extended(self):
        raise NotImplementedError()

    def get_observables(self):
        """Get the physics observables.

        """
        return tuple((self.get(obs_id)
                      if obs_id in self
                      else self.set(obs_id, execute_and_return_self(ROOT.RooRealVar(obs_name, obs_title,
                                                                                    obs_min, obs_max,
                                                                                    unit),
                                                                    'setStringAttribute',
                                                                    'originalName',
                                                                    obs_id)))
                     for obs_id, (obs_name, obs_title, obs_min, obs_max, unit)
                     in self.OBSERVABLES.items())

    def set_observable(self, obs_id, obs=None, name=None, title=None, limits=None, units=None):
        """

        Note:
            If `obs` is given, the other parameters are ignored.

        """
        if obs_id not in self.OBSERVABLES:
            raise KeyError("Unknown observable -> {}".format(obs_id))
        new_config = list(self.OBSERVABLES[obs_id])
        if obs:
            self._objects[obs_id] = obs
            new_config = [obs.GetName(), obs.GetTitle(), obs.getMin(), obs.getMax(), obs.getUnit()]
        else:
            if name:
                new_config[0] = name
                if obs_id in self:
                    self._objects[obs_id].SetName(name)
            if title:
                new_config[1] = title
                if obs_id in self:
                    self._objects[obs_id].SetTitle(title)
            if limits:
                if len(limits) == 2:
                    min_, max_ = limits
                    range_name = ""
                elif len(limits) == 3:
                    range_name, min_, max_ = limits
                new_config[2] = min_
                new_config[3] = max_
                if obs_id in self:
                    self._objects[obs_id].setRange(range_name, min_, max_)
            if units:
                new_config[4] = units
                if obs_id in self:
                    self._objects[obs_id].setUnit(units)
        self.OBSERVABLES[obs_id] = tuple(new_config)

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
        return self._objects.get('Yield', None)

    def set_yield_var(self, yield_):
        raise NotImplementedError()

    def get_category_var(self):
        return self._category

    def get_category_vars(self):
        if not self._category:
            return None
        if isinstance(self._category, ROOT.RooSuperCategory):
            cats = []
            cat_iter = self._category.serverIterator()
            while True:
                cat = cat_iter.Next()
                if not cat:
                    break
                if cat.GetName() not in self._objects:
                    cat = self.set(cat.GetName(), cat)
                cats.append(cat)
            return tuple(cats)
        else:
            return (self._category,)

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

    def __init__(self, config, parameters=None):
        super(PhysicsFactory, self).__init__(config, parameters)
        # Configure yields
        if 'yield' in parameters:
            self.set_yield_var(parameters['yield'])

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Raises:
            NotImplementedError

        """
        raise NotImplementedError()

    def get_unbound_extended_pdf(self, name, title):
        """Get an extended physics PDF.

        Returns:
            `ROOT.RooExtendPdf`.

        Raises:
            ValueError: If the yield had not been configured previously

        """
        return ROOT.RooExtendPdf(name,
                                 title,
                                 self.get_pdf(name+'_{noext}', title+'_{noext}'),
                                 self._objects['Yield'])

    def has_to_be_extended(self):
        return False

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

    def set_yield_var(self, yield_):
        if 'Yield' not in self._objects:
            self._create_parameter('Yield', yield_)
        else:
            if isinstance(yield_, (list, tuple)):
                yield_ = yield_[0]
            if isinstance(self._objects['Yield'], ROOT.RooRealVar):
                if isinstance(yield_, ROOT.RooRealVar):
                    self._objects['Yield'].setVal(yield_.getVal())
                    self._objects['Yield'].SetName(yield_.GetName())
                    self._objects['Yield'].SetTitle(yield_.GetTitle())
                elif isinstance(yield_, (float, int)):
                    self._objects['Yield'].setVal(yield_)
            else:
                logger.warning("Trying to set a yield that cannot be overriden")


# Product Physics Factory
class ProductPhysicsFactory(BaseFactory):
    """RooProdPdf of different observables."""

    PARAMETERS = []  # No extra parameters here

    def __init__(self, factories, parameters=None):
        """Initialize.

        In this case, the children are a map of observable -> Factory.

        """
        super(ProductPhysicsFactory, self).__init__({}, parameters)
        # Set children
        self._children = factories
        # Configure yields
        if 'yield' in parameters:
            self.set_yield_var(parameters['yield'])

    def get_unbound_pdf(self, name, title):
        """Get unbound PDF."""
        pdfs = ROOT.RooArgList()
        for observable, factory in self._children.items():
            new_name = self._add_superscript(name, observable)
            pdfs.add(factory.get_pdf(new_name, new_name))
        return ROOT.RooProdPdf(name, title, pdfs)

    def get_unbound_extended_pdf(self, name, title, yield_val=None):
        """Get an extended physics PDF.

        Returns:
            `ROOT.RooExtendPdf`.

        Raises:
            ValueError: If the yield had not been configured previously

        """
        # Return the extended PDF
        return ROOT.RooExtendPdf(name,
                                 title,
                                 self.get_pdf(name+'_{noext}', title+'_{noext}'),
                                 self._objects['Yield'])

    def has_to_be_extended(self):
        return False

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

    def set_observable(self, obs_id, obs=None, name=None, title=None, limits=None, units=None):
        has_changed = False
        for child in self._children.values():
            try:
                child.set_observable(obs_id, obs, name, title, limits, units)
                has_changed = True
            except KeyError:
                pass
        if not has_changed:
            raise KeyError("Unknown observable -> {}".format(obs_id))

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

    def set_yield_var(self, yield_):
        constraint = None
        if isinstance(yield_, (list, tuple)):
            yield_, constraint = yield_
        if 'Yield' not in self._objects:
            self._objects['Yield'] = yield_
            if constraint:
                self._constraints.add(constraint)
        else:
            if isinstance(self._objects['Yield'], ROOT.RooRealVar):
                self._objects['Yield'].setVal(yield_.getVal())
                self._objects['Yield'].SetName(yield_.GetName())
                self._objects['Yield'].SetTitle(yield_.GetTitle())
            else:
                logger.warning("Trying to set a yield that cannot be overriden")

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

    def __init__(self, factories, children_yields, parameters=None):
        """Initialize.

        In this case, the children are a map of PDF name -> Factory.

        Raises:
            ValueError: When the observables of the factories are incompatible.
            KeyError: On configuration error.

        """
        # Check observable compatibility
        if len({tuple([obs.GetName() for obs in factory.get_observables()])
                for factory in factories.values()}) != 1:
            raise ValueError("Incompatible observables")
        # Check children yields type
        if not isinstance(children_yields, OrderedDict):
            raise ValueError("children_yields must be an ordered dictionary")
        super(SumPhysicsFactory, self).__init__({}, parameters)
        # Set children
        self._children = factories
        # Set observables
        observables = {obs.getStringAttribute('originalName'): obs
                       for obs in self._children.values()[0].get_observables()}
        for obs_name, obs in observables.items():
            for child in self._children.values()[1:]:
                child.set_observable(obs_name, obs=obs)
        # Set yields
        yield_ = None
        if parameters and 'yield' in parameters:
            yield_, constraint = parameters.pop('yield')
        yield_values = [child_yield for child_yield, _ in children_yields.values()]
        if len(factories) == len(children_yields):  # Extended
            if yield_ is not None:
                raise KeyError("Specified yield on a sum of RooExtendPdf")
            self._objects['Yield'] = ROOT.RooAddition("Yield", "Yield", list_to_rooarglist(yield_values))
            self._constraints.update({constraint for _, constraint in children_yields.values()})
            for child_name, child in self._children.items():
                child.set_yield_var(children_yields[child_name])
        elif (len(factories) - len(children_yields)) == 1:
            # Check order is correct
            if self._children.keys()[-1] in children_yields.keys():
                logger.error("The last child should not be in `children_keys` to ensure consistency.")
                raise ValueError("Wrong PDF ordering")
            # Store the fractions and propagate
            for yield_val in yield_values:
                if yield_val.getVal() > 1:
                    raise ValueError("Specified a fraction larger than 1 -> {}".format(yield_val.GetName()))
                # Not very good heuristics
                if yield_val.getStringAttribute('shared') != 'true':
                    yield_val.SetName(yield_val.GetName().replace('Yield', 'Fraction'))
                    yield_val.SetTitle(yield_val.GetTitle().replace('Yield', 'Fraction'))
            self._objects['Fractions'] = yield_values
            for child_name, child in self._children.items():
                if child_name in children_yields.keys():
                    child_yield, child_constraint = children_yields[child_name]
                    child['Fraction'] = child_yield
                    child._constraints.add(child_constraint)
                else:
                    # Need no rename because RooFracRemainder needs a RooArgSet and there will be clashes
                    # between vars named 'Fraction'. It's stupid, since the name is not used after.
                    for yield_num, yield_val in enumerate(yield_values):
                        yield_val.SetName('{}_{}'.format(yield_val.GetName(), yield_num))
                    child['Fraction'] = ROOT.RooFracRemainder("Fraction", "Fraction", list_to_rooargset(yield_values))
                    child._constraints.update({constraint
                                               for _, constraint in children_yields.values()
                                               if constraint})
                    # Put names back where they belong
                    for yield_num, yield_val in enumerate(yield_values):
                        yield_val.SetName('_'.join(yield_val.GetName().split('_')[:-1]))
            # Final rename
            if yield_ is not None:
                self.set_yield_var((yield_, constraint))
        else:
            raise KeyError("Badly specified yields/fractions")

    def get_unbound_pdf(self, name, title):
        if 'Fractions' not in self:
            logger.warning("Requested non-extended PDF on a RooAddPdf made of ExtendedPdf. "
                           "Returning an extended PDF")
            return self.get_extended_pdf(name, title)
        pdfs = ROOT.RooArgList()
        for child_name, child in self._children.items():
            new_name = self._add_superscript(name, child_name)
            pdfs.add(child.get_pdf(new_name, new_name))
        return ROOT.RooAddPdf(name, title,
                              pdfs,
                              list_to_rooarglist(self._objects['Fractions']))

    def get_unbound_extended_pdf(self, name, title):
        if 'Fractions' in self:
            # Create non-extended PDF and extend
            return ROOT.RooExtendPdf(name,
                                     title,
                                     self.get_pdf(name+'_{noext}', title+'_{noext}'),
                                     self._objects['Yield'])
        else:
            pdfs = ROOT.RooArgList()
            for child_name, child in self._children.items():
                new_name = self._add_superscript(name, child_name)
                pdfs.add(child.get_extended_pdf(new_name, new_name))
            return ROOT.RooAddPdf(name, title, pdfs)

    def has_to_be_extended(self):
        return 'Fractions' not in self

    def get_observables(self):
        """Get the physics observables.

        Returns:
            tuple: Observables in factory order.

        Raises:
            NotInitializedError: If `__call__` has not been called.

        """
        return self._children.values()[0].get_observables()

    def set_observable(self, obs_id, obs=None, name=None, title=None, limits=None, units=None):
        for child in self._children.values():
            child.set_observable(obs_id, obs, name, title, limits, units)

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

    def set_yield_var(self, yield_):
        if 'Fractions' not in self._objects:
            logger.warning("Trying to set the yield of an Extended RooAddPdf. Ignoring.")
        elif 'Yield' not in self._objects:
            yield_ = self._create_parameter('Yield', yield_)
            for child in self._children.values():
                if 'Yield' in child:
                    raise ValueError("Inconsistent state: trying to set the yield of an already configured Factory.")
                # Again, not very good heuristics
                child.set_yield_var(ROOT.RooProduct(child['Fraction'].GetName().replace('Fraction', 'Yield'),
                                                    child['Fraction'].GetTitle().replace('Fraction', 'Yield'),
                                                    list_to_rooarglist([yield_, child['Fraction']])))
        else:
            if isinstance(self._objects['Yield'], ROOT.RooRealVar):
                if isinstance(yield_, ROOT.RooRealVar):
                    self._objects['Yield'].setVal(yield_.getVal())
                    self._objects['Yield'].SetName(yield_.GetName())
                    self._objects['Yield'].SetTitle(yield_.GetTitle())
                elif isinstance(yield_, (float, int)):
                    self._objects['Yield'].setVal(yield_)
            else:
                logger.warning("Trying to set a yield that cannot be overriden")

    def transform_dataset(self, dataset):
        """Transform dataset according to the factory configuration.

        Since all PDFs of the addition are supposed to need the same transformation,
        the dataset is transformed according to the first one

        Arguments:
            dataset (pandas.DataFrame): Data frame to fold.

        Returns:
            `pandas.DataFrame`: Input dataset with the transformation applied.

        """
        return self._children.values()[0].transform_dataset(dataset)


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
            sim_pdf.addPdf(child.get_pdf(new_name, new_name),
                           '{{{}}}'.format(category)
                           if category.count(';') > 0
                           else category)
        return sim_pdf

    def get_unbound_extended_pdf(self, name, title):
        sim_pdf = ROOT.RooSimultaneous(name, title, self._category)
        yields = ROOT.RooArgList()
        for category, child in self._children.items():
            new_name = self._add_superscript(name, category)
            sim_pdf.addPdf(child.get_extended_pdf(new_name, new_name),
                           '{{{}}}'.format(category)
                           if category.count(';') > 0
                           else category)
            yields.add(child.get_yield_var())
        self._objects['Yield'] = ROOT.RooAddition('Yield', 'Yield', yields)
        return sim_pdf

    def is_extended(self):
        children_are_extended = (child.is_extended()
                                 for child in self.get_children().values())
        if all(children_are_extended):
            return True
        elif any(children_are_extended):
            # Mix of children, a bit inconsistent
            raise ValueError("Inconsistent children state")
        else:
            return False

    def has_to_be_extended(self):
        return any(child.has_to_be_extended()
                   for child in self.get_children().values())

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

    def set_observable(self, obs_id, obs=None, name=None, title=None, limits=None, units=None):
        has_changed = False
        for child in self._children.values():
            try:
                child.set_observable(obs_id, obs, name, title, limits, units)
                has_changed = True
            except KeyError:
                pass
        if not has_changed:
            raise KeyError("Unknown observable -> {}".format(obs_id))

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

        Note:
            For the category, a column named after the category variable is searched
            for. If not found, the 'category' column is used.

        Arguments:
            dataset (pandas.DataFrame): Data frame to fold.

        Returns:
            `pandas.DataFrame`: Input dataset with the transformation applied.

        Raises:
            ValueError: When the dataset contains categories that have not been configured
                in the class.
            KeyError: If the category is not found in the dataset.

        """
        cat_var = self._category.GetName()
        if cat_var not in dataset.columns:
            cat_var = 'category'
            if cat_var not in dataset.columns:
                raise KeyError("Category var not found in dataset -> {}".format(self._category.GetName()))
        categories = dataset.groupby(cat_var).indices.keys()
        # A simple check
        if not set(categories).issubset(set(self._children.keys())):
            raise ValueError("Dataset contains categories not defined in the SimultaneousPhysicsFactory")
        for category in categories:
            dataset.loc[dataset[cat_var] == category] = self._children[category] \
                .transform_dataset(dataset[dataset[cat_var] == category].copy())
        return dataset


# EOF
