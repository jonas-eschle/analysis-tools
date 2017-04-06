#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   21.03.2017
# =============================================================================
"""Acceptance management."""

import os

import analysis.utils.paths as _path
import analysis.utils.config as _config
from analysis.efficiency import get_efficiency_model

from .acceptance import Acceptance


def load_acceptance(name):
    """Load an acceptance configuration file.

    The file path is determined from the `name` using the `paths.get_acceptance_path`
    function.

    Arguments:
        name (str): Name of the acceptance.

    Returns:
        `analysis.acceptance.Acceptance`: Acceptance object.

    Raises:
        OSError: If the efficiecny file does not exist.
        analysis.utils.config.ConfigError: If there is a problem with the efficiency model.

    """
    # pylint: disable=E1101
    path = _path.get_acceptance_path(name)
    if not os.path.exists(path):
        raise OSError("Cannot find efficiency file -> %s" % path)
    return get_acceptance(_config.load_config(path,
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
        `analysis.acceptance.acceptance.Acceptance`: Acceptance object.

    Raises:
        analysis.utils.config.ConfigError: If the input config is missing keys.
        See `analysis.utils.config.load_config`.

    """
    if any(key not in config for key in ('variables', 'generation', 'reconstruction')):
        raise _config.ConfigError("Missing configuration key!")
    # pylint: disable=E1101
    generation_config = _config.load_config(_path.get_efficiency_path(config['generation']['name']),
                                            validate=['model',
                                                      'variables',
                                                      'parameters'])
    if 'rename-vars' in config['generation']:
        generation_config.update({'rename-vars': config['generation']['rename-vars']})
    # pylint: disable=E1101
    reconstruction_config = _config.load_config(_path.get_efficiency_path(config['reconstruction']['name']),
                                                validate=['model',
                                                          'variables',
                                                          'parameters'])
    if 'rename-vars' in config['reconstruction']:
        reconstruction_config.update({'rename-vars': config['reconstruction']['rename-vars']})
    # Load the efficiencies
    gen_efficiency = get_efficiency_model(generation_config)
    reco_efficiency = get_efficiency_model(reconstruction_config)
    # Check the variables
    if set(config['variables']) != set(gen_efficiency.get_variables()):
        raise _config.ConfigError("Mismatch in variables between acceptance and generation")
    if set(config['variables']) != set(reco_efficiency.get_variables()):
        raise _config.ConfigError("Mismatch in variables between acceptance and reconstruction")
    # Now create the acceptance
    return Acceptance(config['variables'],
                      gen_efficiency,
                      reco_efficiency)

# EOF
