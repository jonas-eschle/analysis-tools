#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   12.01.2017
# =============================================================================
"""Physics utilities."""

from analysis import get_global_var
from analysis.utils.logging_color import get_logger

from .factory import ProductPhysicsFactory


logger = get_logger('analysis.physics')


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
def get_physics_factory(pdf_configs):
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
    if len(pdf_configs) == 1:
        config_name = pdf_configs.keys()[0].lower()
        config = pdf_configs.values()[0]
        return factories[config_name][config['pdf'].lower()](**config)
    else:
        return ProductPhysicsFactory([factories[observable.lower()][config['pdf'].lower()]
                                      for observable, config in pdf_configs.items()])(pdf_configs.values())

# EOF
