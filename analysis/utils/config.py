#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   config.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.01.2017
# =============================================================================
"""Configuration files."""

import os

import yaml

import ROOT

from analysis.utils.logging_color import get_logger


logger = get_logger('analysis.utils.config')


def load_config(*file_names, **options):
    """Load configuration from YAML files.

    If more than one is specified, they are loaded in the order given
    in the function call. Therefore, the latter will override the former
    if key overlap exists.
    Currently supported options are:
        - validate, which gets a list of keys to check. If one of these
            keys is not present, `config.ConfigError` is raised.

    Arguments:
        *file_names (list[str]): Files to load.
        **options (dict): Configuration options. See above for supported
            options.

    Returns:
        dict: Configuration.

    Raises:
        OSError: If some file does not exist.
        ConfigError: If validation fails.

    """
    unfolded_data = []
    for file_name in file_names:
        if not os.path.exists(file_name):
            raise OSError("Cannot file config file -> %s" % file_name)
        try:
            with open(file_name) as input_obj:
                unfolded_data.extend(unfold_config(yaml.load(input_obj)))
        except yaml.parser.ParserError as error:
            raise KeyError(str(error))
    data = fold_config(unfolded_data)
    logger.debug('Loaded configuration -> %s',
                 data)
    if 'validate' in options:
        missing_keys = []
        data_keys = ['/'.join(key.split('/')[:entry_num+1])
                     for key, _ in unfolded_data
                     for entry_num in range(len(key.split('/')))]
        logger.debug("Validating against the followinf keys -> %s",
                     ', '.join(data_keys))
        for key in options['validate']:
            if key not in data_keys:
                missing_keys.append(key)
        if missing_keys:
            raise ConfigError(missing_keys)
    return data


def write_config(config, file_name):
    """Write configuration to file.

    Arguments:
        config (dict): Configuration file.
        file_name (str): Output file.

    """
    with open(file_name, 'w') as output_file:
        yaml.dump(config,
                  output_file,
                  default_flow_style=False,
                  allow_unicode=True,
                  indent=4)


def compare_configs(config1, config2):
    """Compare two configuration files.

    Arguments:
        config1 (dict): First configuration.
        config2 (dict): Second configuration

    Returns:
        set: Keys that are different between the two configs,
            taking into account the values and the fact they are
            present in only one or the other.

    """
    return {key for key, _
            in set.symmetric_difference(unfold_config(config1),
                                        unfold_config(config2))}


# Helpers
def unfold_config(dictionary):
    """Convert a dictionary to a list of key, value pairs.

    Unfolding is done a la viewitems, but recursively.

    Arguments:
        dictionary (dict): Dictionary to update.

    Returns:
        set: Unfolded dictionary.

    """
    output_list = []
    for key, val in dictionary.viewitems():
        if isinstance(val, dict):
            for sub_key, sub_val in unfold_config(val):
                output_list.append(('%s/%s' % (key, sub_key), sub_val))
        else:
            output_list.append((key, val))
    return output_list


def fold_config(unfolded_data):
    """Convert an unfolded dictionary (a la viewitems) back to a dictionary.

    Note:
        If a key is specified more than once, the latest value is taken.

    Arguments:
        unfolded_data (iterable): Data to fold

    Returns:
        dict

    """
    output_dict = {}
    for key, value in unfolded_data:
        current_level = output_dict
        for sub_key in key.split('/'):
            previous_level = current_level
            if sub_key not in current_level:
                current_level[sub_key] = {}
            current_level = current_level[sub_key]
        # pylint: disable=W0631
        previous_level[sub_key] = value
    return output_dict


# Interpretation
def configure_parameter(parameter, parameter_config):
    """Configure a parameter according to a configuration string.

    The configuration string consists in two parts. The first one
    consists in a letter that indicates the "action" to apply on the parameter,
    followed by the configuration of that action. There are several possibilities:
        * 'I' is used for free parameters. Only one argument is required: its
        initial value.
        * 'F' indicates a fixed parameter. The following argument indicates
        at which value to fix it.
        * 'G' is used for a Gaussian-constrained parameter. The arguments of that
        Gaussian, ie, its mean and sigma, have to be given after the letter.
        * 'L' is used for a limited parameter. Initial value, lower limit and
        upper limit follow.

    Arguments:
        parameter (ROOT.RooRealVar): Variable to configure.

    Returns:
        ROOT.RooGaussian: External constraint to apply to the parameter
            (if requested by the configuration). If no constraint has been
            required, None is returned.

    Raises:
        KeyError: If the specified action is unknown.
        ValueError: If the number of arguments after the action is not
            correct.

    """
    constraint = None
    parameter_name = parameter.GetName()
    # Do something with it
    action_params = parameter_config.split()
    action = action_params.pop(0)
    parameter.setVal(float(action_params[0]))
    if action == 'I':  # Free parameter, we specify its initial value
        parameter.setConstant(False)
    elif action == 'F':  # Fixed parameter
        parameter.setConstant(True)
    elif action == 'G':  # Gaussian constraint
        try:
            initial_value, sigma = action_params
        except ValueError:
            raise ValueError(action_params)
        constraint = ROOT.RooGaussian(parameter_name + 'Constraint',
                                      parameter_name + 'Constraint',
                                      parameter,
                                      ROOT.RooFit.RooConst(float(initial_value)),
                                      ROOT.RooFit.RooConst(float(sigma)))
        parameter.setConstant(False)
    elif action == 'L':  # Uniform constraint -> set limits
        _, min_val, max_val = action_params
        parameter.setMin(float(min_val))
        parameter.setMax(float(max_val))
        parameter.setConstant(False)
    else:
        raise KeyError(action)
    return constraint


# Exceptions
class ConfigError(Exception):
    """Error in loading configuration file."""

    def __init__(self, missing_keys):
        """Initialize exception.

        Arguments:
            missing_keys (list): Missing keys after validation.

        """
        self.missing_keys = missing_keys
        super(ConfigError, self).__init__("Failed validation: %s are missing",
                                          ','.join(missing_keys))

# EOF
