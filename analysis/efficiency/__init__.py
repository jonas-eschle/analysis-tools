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
from analysis.utils.config import load_config, ConfigError
# pylint: disable=E0611
from analysis.utils.paths import get_efficiency_path, get_acceptance_path
from analysis.utils.logging_color import get_logger

from .legendre import _EFFICIENCY_MODELS as _LEG_EFFICIENCY_MODELS

from .acceptance import Acceptance


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
for eff_name, class_ in _LEG_EFFICIENCY_MODELS.items():
    register_efficiency_model(eff_name, class_)


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


def load_acceptance(name):
    """Load an acceptance configuration file.

    The file path is determined from the `name` using the `paths.get_acceptance_path`
    function.

    Arguments:
        name (str): Name of the acceptance.

    Returns:
        `analysis.efficiency.Acceptance`: Acceptance object.

    Raises:
        OSError: If the efficiecny file does not exist.
        analysis.utils.config.ConfigError: If there is a problem with the efficiency model.

    """
    # pylint: disable=E1101
    path = get_acceptance_path(name)
    if not os.path.exists(path):
        raise OSError("Cannot find efficiency file -> %s" % path)
    return get_acceptance(load_config(path,
                                      validate=('variables', 'generation', 'reconstruction')))


def get_acceptance(config):
    """Get an acceptance object.

    Arguments:
        config (dict): Acceptance to load. Its keys are:
            + `variables` (list[str]): List of variable names.
            + `generation` (dict): Generation configuration. Its keys are:
                - `name` (str): Name of the generator shape fit.
                - `rename-vars` (dict, optional): Rename variables from the original efficiency
                    to adapt them to different datasets.
            + `reconstruction` (dict): Reconstruction efficiency configuration. Its keys are:
                - `name` (str): Name of the reconstruction shape fit.
                - `rename-vars` (dict, optional): Rename variables from the original efficiency
                    to adapt them to different datasets.

    Returns:
        `analysis.efficiency.acceptance.Acceptance`: Acceptance object.

    Raises:
        analysis.utils.config.ConfigError: If the input config is missing keys.
        See `analysis.utils.config.load_config`.

    """
    if any(key not in config for key in ('variables', 'generation', 'reconstruction')):
        raise ConfigError("Missing configuration key!")
    # pylint: disable=E1101
    generation_config = load_config(get_efficiency_path(config['generation']['name']),
                                    validate=('model', 'variables', 'parameters'))
    if 'rename-vars' in config['generation']:
        generation_config.update({'rename-vars': config['generation']['rename-vars']})
    # pylint: disable=E1101
    reconstruction_config = load_config(get_efficiency_path(config['reconstruction']['name']),
                                        validate=('model', 'variables', 'parameters'))
    if 'rename-vars' in config['reconstruction']:
        reconstruction_config.update({'rename-vars': config['reconstruction']['rename-vars']})
    # Load the efficiencies
    gen_efficiency = get_efficiency_model(generation_config)
    reco_efficiency = get_efficiency_model(reconstruction_config)
    # Check the variables
    if set(config['variables']) != set(gen_efficiency.get_variables()):
        raise ConfigError("Mismatch in variables between acceptance and generation")
    if set(config['variables']) != set(reco_efficiency.get_variables()):
        raise ConfigError("Mismatch in variables between acceptance and reconstruction")
    # Now create the acceptance
    return Acceptance(config['variables'],
                      gen_efficiency,
                      reco_efficiency)

# EOF
