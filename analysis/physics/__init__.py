#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   16.04.2017
# =============================================================================
"""Physics utilities."""

from collections import OrderedDict, defaultdict
import traceback

import ROOT

from analysis import get_global_var
from analysis.utils.logging_color import get_logger
from analysis.utils.config import fold_config, unfold_config, configure_parameter


logger = get_logger('analysis.physics')
# logger.setLevel(10)

# Infinitely recursed defultdict
recurse_dict = lambda: defaultdict(recurse_dict)


# def unfold_ordereddict(ordered_dict):
#     if isinstance(ordered_dict, OrderedDict):
#         return {key: unfold(value) for key, value in ordered_dict.items()}
#     else:
#         return ordered_dict


def register_physics_factories(observable, factories):
    """Register a physics factory.

    This model then becomes available to `get_efficiency_model` functions.

    Arguments:
        observable (str): Observable name.
        factories (dict): Factory name -> factory class mapping.

    Returns:
        int: Number of registered physics factories for the given observable.

    """
    logger.debug("Registering factories for the '%s' observable -> %s", observable, factories)
    get_global_var('PHYSICS_FACTORIES')[observable].update(factories)
    return len(get_global_var('PHYSICS_FACTORIES')[observable])


# Factory loading
def get_physics_factory(observable, pdf_type):
    """Get physics factory.

    Arguments:
        pdf_configs (dict): PDFs to load, along with their configuration.
            The keys define the type of observable.

    Returns:
        `PhysicsFactory`: Requested PhysicsFactory.

    Raises:
        KeyError: If the type of factory is unknown.

    """
    factories = get_global_var('PHYSICS_FACTORIES')
    if observable not in factories:
        raise KeyError("Unknown observable type -> %s" % observable)
    if pdf_type not in factories[observable]:
        raise KeyError("Unknown PDF type -> %s" % pdf_type)
    return factories[observable][pdf_type]


# Load and configure physics factory
def rename_on_recursion_end(func):
    """Perform a recursive rename at the end of the configuration recursion.

    Raises:
        RuntimeError: If the wrapped function doesn't return a physics
            factory.

    """
    def wrapped(*args, **kwargs):
        """Check the parent caller to determine when to rename.

        Raises:
            RuntimeError: If the wrapped function doesn't return a physics
                factory.

        """
        import analysis.physics.factory as factory
        res_factory = func(*args, **kwargs)
        if not isinstance(res_factory, factory.BaseFactory):
            raise RuntimeError("rename_on_recursion_end used on a non-compliant function.")
        if len([frame[2]
                for frame in traceback.extract_stack()
                if frame[2] == func.func_name]) == 0:
            res_factory.rename_children_parameters()
        return res_factory
    return wrapped


@rename_on_recursion_end
def configure_model(config, shared_vars=None):
    """

    Raises:
        ValueError: If the shared parameters are badly configured.

    """
    def configure_factory(observable, config, shared_vars=None):
        logger.debug("Configuring factory -> %s", dict(config))
        return get_physics_factory(observable, config['pdf'])(config,
                                                              shared_vars['parameters'])

    def configure_prod_factory(config, shared_vars=None):
        logger.debug("Configuring product -> %s", config['pdf'])
        params = config.get('parameters', {})
        params.update(config['pdf'].pop('parameters', {}))
        if not params:
            params = None
        factories = OrderedDict((observable,
                                 configure_factory(observable,
                                                   factory_config,
                                                   shared_vars['pdf'][observable]))
                                for observable, factory_config in config['pdf'].items())
        if len(factories) == 1:
            return factories.values()[0]
        else:
            return factory.ProductPhysicsFactory(factories, parameters=params)

    def configure_sum_factory(config, shared_vars=None):
        logger.debug("Configuring sum -> %s", dict(config))
        factories = OrderedDict()
        for pdf_name, pdf_config in config.items():
            if 'parameters' not in pdf_config:
                pdf_config['parameters'] = OrderedDict()
            pdf_config['parameters'].update(config.get('parameters', {}))
            if isinstance(pdf_config.get('pdf', None), str):
                factories[pdf_name] = configure_model({pdf_name: pdf_config}, shared_vars)
            else:
                factories[pdf_name] = configure_model(pdf_config, shared_vars[pdf_name])
        if len(factories) == 1:
            return factories.values()[0]
        else:
            return factory.SumPhysicsFactory(factories)

    def configure_simul_factory(config, shared_vars=None):
        logger.debug("Configuring simultaneous -> %s", dict(config))
        categories = config['categories'].split(',') \
            if isinstance(config['categories'], str) \
            else config['categories']
        cat_list = []
        if len(categories) == 1:
            cat = ROOT.RooCategory(categories[0], categories[0])
            cat_list.append(cat)
        else:
            cat_set = ROOT.RooArgSet()
            for cat_name in categories:
                cat_list.append(ROOT.RooCategory(cat_name, cat_name))
                cat_set.add(cat_list[-1])
            cat = ROOT.RooSuperCategory('x'.join(categories),
                                        'x'.join(categories),
                                        cat_set)
        for cat_label in config['pdf'].keys():
            for cat_iter, cat_sublabel in enumerate(cat_label.split(',')):
                cat_list[cat_iter].defineType(cat_sublabel.replace(' ', ''))
        sim_factory = factory.SimultaneousPhysicsFactory({tuple(cat_label.replace(' ', '').split(',')):
                                                          configure_model(cat_config,
                                                                          shared_vars['pdf'][cat_label])
                                                          for cat_label, cat_config in config['pdf'].items()},
                                                         cat)
        for cat in cat_list:
            sim_factory.set('cat_%s' % cat.GetName(), cat)
        return sim_factory

    import analysis.physics.factory as factory
    # Prepare shared variables
    if shared_vars is None:
        # Create shared vars
        parameter_configs = {config_element: config_value
                             for config_element, config_value in unfold_config(config)
                             if isinstance(config_value, str) and config_value.startswith('@')}
        # First build the shared var
        refs = {}
        constraints = []
        for config_element, config_value in parameter_configs.items():
            split_element = config_value[1:].split('/')
            if len(split_element) == 4:
                ref_name, var_name, var_title, var_config = split_element
                if ref_name in refs:
                    raise ValueError("Shared parameter defined twice -> %s" % ref_name)
                var = ROOT.RooRealVar(var_name, var_title, 0.0)
                constraints.append(configure_parameter(var, var_config))
                refs[ref_name] = var
            elif len(split_element) == 1:
                pass
            else:
                raise ValueError("Badly configured shared parameter -> %s: %s" % (config_element, config_value))
        # Now replace the refs by the shared variables
        shared_vars = fold_config({config_element: refs[ref_val.split('/')[0][1:]]
                                   for config_element, ref_val in parameter_configs.items()}.viewitems(),
                                  recurse_dict)
    # Let's find out what is this
    if 'categories' in config:
        return configure_simul_factory(config, shared_vars)
    else:
        if 'pdf' not in config:
            if isinstance(config.values()[0]['pdf'], str):
                shared = recurse_dict()
                shared['pdf'] = shared_vars
                return configure_prod_factory({'pdf': config}, shared)
            else:
                return configure_sum_factory(config, shared_vars)
        else:
            if len(config['pdf']) > 1:
                return configure_prod_factory(config, shared_vars)
            else:
                pdf_obs = config['pdf'].keys()[0]
                pdf_config = config['pdf'].values()[0]
                if 'parameters' not in pdf_config:
                    pdf_config['parameters'] = OrderedDict()
                pdf_config['parameters'].update(config.get('parameters'))
                sh_vars = shared_vars['pdf'][pdf_obs].copy()
                if 'parameters' in sh_vars:
                    sh_vars['parameters'].update(shared_vars['parameters'])
                else:
                    sh_vars['parameters'] = shared_vars['parameters']
                return configure_factory(pdf_obs, pdf_config, sh_vars)
    raise RuntimeError()


# EOF
