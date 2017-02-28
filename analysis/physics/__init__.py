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
        pdf_configs (list): List of PDFs to load, along with their configuration.

    Returns:
        `PhysicsFactory`: Requested PhysicsFactory.

    Raises:
        KeyError: If the type of factory is unknown.

    """
    factories = get_global_var('PHYSICS_FACTORIES')
    if not isinstance(pdf_configs, (list, tuple)):
        pdf_configs = [pdf_configs]
    if len(pdf_configs) == 1:
        return factories[pdf_configs[0]['observables']][pdf_configs[0]['type']](**pdf_configs[0])
    else:
        return ProductPhysicsFactory([factories[pdf_config['observables']][pdf_config['type']]
                                      for pdf_config in pdf_configs])(pdf_configs)

# EOF
