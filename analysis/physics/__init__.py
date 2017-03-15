#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   12.01.2017
# =============================================================================
"""Physics utilities."""

from analysis import get_global_var

from .factory import ProductPhysicsFactory


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
        return factories[pdf_configs.keys()[0]][pdf_configs.values()[0]['pdf']](**pdf_configs.values()[0])
    else:
        return ProductPhysicsFactory([factories[observable][config['pdf']]
                                      for observable, config in pdf_configs.items()])(pdf_configs.values())

# EOF
