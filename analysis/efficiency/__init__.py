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
from analysis.utils.config import load_config, ConfigError, unfold_config
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
    return get_global_var('EFFICIENCY_MODELS').get(model_name.lower())


def load_efficiency_model(model_name, **extra_parameters):
    """Load efficiency from file.

    The file path is determined from the `name` using the `paths.get_efficiency_path`
    function.

    Arguments:
        model_name (str): Name of the efficiency model.
        **extra_parameters (dict): Extra configuration parameters to override the entries
            in the `parameters` node loaded from the efficiency file.

    Raises:
        OSError: If the efficiency file does not exist.
        analysis.utils.config.ConfigError: If there is a problem with the efficiency model.

    """
    path = get_efficiency_path(model_name)
    if not os.path.exists(path):
        raise OSError("Cannot find efficiency file -> %s" % path)
    config = load_config(path, validate=('model', 'variables', 'parameters'))
    return get_efficiency_model(config, **extra_parameters)


def get_efficiency_model(efficiency_config, **extra_parameters):
    """Get efficiency model class.

    User-defined models, stored in the `EFFICIENCY_MODELS` global variable,
    take precedence.

    Arguments:
        efficiency_config (dict): Efficiency configuration.
        **extra_parameters (dict): Extra configuration parameters to override the entries
            in the `parameters` node in `efficiency_config`.

    Returns:
        `analysis.efficiency.efficiency.Efficiency`: Efficiency object.

    Raises:
        KeyError: If there is a configuration error

    """
    efficiency_config['parameters'].update(extra_parameters)
    # Check the configuration
    for key in ('model', 'variables', 'parameters'):
        if key not in efficiency_config:
            raise KeyError("Bad configuration -> '%s' key is missing" % key)
    # Now load efficiency
    model = get_efficiency_model_class(efficiency_config['model'])
    if not model:
        raise KeyError("Unknown efficiency model -> '%s'" % efficiency_config['model'])
    return model(efficiency_config['variables'], efficiency_config['parameters'])


def load_acceptance(name, **extra_parameters):
    """Load an acceptance configuration file.

    The file path is determined from the `name` using the `paths.get_acceptance_path`
    function.

    Note:
        For the exact configuration, see `get_acceptance`.

    Arguments:
        name (str): Name of the acceptance.
        **extra_parameters (dict): Extra configuration parameters to override the entries
            in the `parameters` nodes from the `generation` and `reconstruction` efficiencies.
            As such, the extra parameters need to be placed under the `generation` or
            `reconstruction` keys. For example:

                >>> load_acceptance('Test',
                                    reconstruction={'rename-vars':{'acc_q2':'q2',
                                                                   'acc_cosThetaL':'ctl'}})

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
    config = load_config(path, validate=('variables', 'generation', 'reconstruction'))
    config['generation'].update(extra_parameters.get('generation', {}))
    config['reconstruction'].update(extra_parameters.get('reconstruction', {}))
    return get_acceptance(config)


def get_acceptance(config):
    """Get an acceptance object.

    Arguments:
        config (dict): Acceptance to load. Its keys are:
            + `variables` (list[str]): List of variable names.
            + `generation` (dict): Generation configuration. It needs to have a `name` entry, which corresponds
                to the name of the generator efficiency. Any other key will be passed to `get_efficiency` as
                `extra_parameters`
            + `reconstruction` (dict): Reconstruction configuration. It needs to have a `name` entry, which corresponds
                to the name of the reconstruction efficiency. Any other key will be passed to `get_efficiency` as
                `extra_parameters`

    Returns:
        `analysis.efficiency.acceptance.Acceptance`: Acceptance object.

    Raises:
        analysis.utils.config.ConfigError: If the input config is missing keys.
        See `analysis.utils.config.load_config`.

    """
    config_keys = [key for key, _ in unfold_config(config)]
    # missing_keys should be empty if the needed keys have been provided. Otherwise complain!
    missing_keys = set(('variables', 'generation/name', 'reconstruction/name')) - set(config_keys)

    if missing_keys:
        raise ConfigError("Missing configuration key! -> {}".format(missing_keys))
    # Load the efficiencies
    gen_efficiency = get_efficiency_model(load_config(get_efficiency_path(config['generation'].pop('name')),
                                                      validate=('model', 'variables', 'parameters')),
                                          **config['generation'])
    reco_efficiency = get_efficiency_model(load_config(get_efficiency_path(config['reconstruction'].pop('name')),
                                                       validate=('model', 'variables', 'parameters')),
                                           **config['reconstruction'])
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
