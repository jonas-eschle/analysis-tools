#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   21.03.2017
# =============================================================================
"""Efficiency classes and utilities."""

import os

from analysis import get_global_var
from analysis.utils.paths import get_efficiency_path
from analysis.utils.config import load_config

from .legendre import _EFFICIENCY_MODELS as _LEG_EFFICIENCY_MODELS

_EFFICIENCY_MODELS = [_LEG_EFFICIENCY_MODELS]


def get_efficiency_model_class(model_name):
    """Load the efficiency class.

    Arguments:
        model_name (str): Name of the efficiency model class.

    Returns:
        `Efficiency`: Efficiency class, non-instantiated.

    """
    # Load predefined models
    efficiency_models = {}
    for eff_model in _EFFICIENCY_MODELS:
        efficiency_models.update(eff_model)
    # Add user defined models
    efficiency_models.update(get_global_var('EFFICIENCY_MODELS'))
    return efficiency_models.get(model_name.lower(), None)


def load_efficiency_model(name):
    """Load efficiency from file.

    The file path is determined from the `name` using the `paths.get_efficiency_path`
    function.

    Arguments:
        name (str): Name of the efficiency model.

    Raises:
        OSError: If the efficiecny file does not exist.
        analysis.utils.config.ConfigError: If there is a problem with the efficiency model.

    """
    path = get_efficiency_path(name)
    if not os.path.exists(path):
        raise OSError("Cannot find efficiency file -> %s" % path)
    return get_efficiency_model(load_config(path,
                                            validate=('model', 'variables', 'parameters')))


def get_efficiency_model(efficiency_config):
    """Get efficiency model class.

    User-defined models, stored in the `EFFICIENCY_MODELS` global variable,
    take precedence.

    If `rename-vars` is given, the `rename_variables` method of the efficiency
    model is executed before returning it.

    Arguments:
        efficiency_config (dict): Efficiency configuration.

    Returns:
        `analysis.efficiency.efficiency.Efficiency`: Efficiency object.

    Raises:
        KeyError: If there is a configuration error

    """
    # Check the configuration
    for key in ('model', 'variables', 'parameters'):
        if key not in efficiency_config:
            raise KeyError("Bad configuration -> '%s' key is missing" % key)
    # Now load efficiency
    model = get_efficiency_model_class(efficiency_config['model'])
    if not model:
        raise KeyError("Unknown efficiency model -> '%s'" % efficiency_config['model'])
    eff_model = model(efficiency_config['variables'], efficiency_config['parameters'])
    if 'rename-vars' in efficiency_config:
        eff_model.rename_variables(efficiency_config['rename-vars'])
    return eff_model

# EOF
