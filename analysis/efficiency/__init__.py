#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   21.03.2017
# =============================================================================
"""Efficiency classes and utilities.

Note that the default efficiency models are not loaded into the global variables
until this module is imported.

"""

import os

from analysis import get_global_var
from analysis.utils.config import load_config
# pylint: disable=E0611
from analysis.utils.paths import get_efficiency_path
from analysis.utils.logging_color import get_logger


from .legendre import _EFFICIENCY_MODELS as _LEG_EFFICIENCY_MODELS


logger = get_logger('analysis.efficiency')


def register_efficiency_model(model_name, model_class):
    """Register an efficiency model.

    This model then becomes available to `get_efficiency_model` functions.

    Arguments:
        model_name (str): Name of the model.
        model_class (`Efficiency`): Efficiency model to register.

    Returns:
        int: Number of registered efficiency models

    """
    logger.debug("Registering efficiency model -> %s", model_name)
    get_global_var('EFFICIENCY_MODELS').update({model_name: model_class})
    return len(get_global_var('EFFICIENCY_MODELS'))


# Register our models
for name, class_ in _LEG_EFFICIENCY_MODELS.items():
    register_efficiency_model(name, class_)


def get_efficiency_model_class(model_name):
    """Load the efficiency class.

    Arguments:
        model_name (str): Name of the efficiency model class.

    Returns:
        `Efficiency`: Efficiency class, non-instantiated.

    """
    return get_global_var('EFFICIENCY_MODELS').get(model_name.lower(), None)


def load_efficiency_model(model_name):
    """Load efficiency from file.

    The file path is determined from the `name` using the `paths.get_efficiency_path`
    function.

    Arguments:
        model_name (str): Name of the efficiency model.

    Raises:
        OSError: If the efficiecny file does not exist.
        analysis.utils.config.ConfigError: If there is a problem with the efficiency model.

    """
    path = get_efficiency_path(model_name)
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
