#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   config.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.01.2017
# =============================================================================
"""Configuration files."""
from __future__ import print_function, division, absolute_import

import os
import random
import string

from collections import OrderedDict, defaultdict

import yaml
import yamlordereddictloader

from analysis.utils.logging_color import get_logger


logger = get_logger('analysis.utils.config')


def load_config(*file_names, **options):
    """Load configuration from YAML files.

    If more than one is specified, they are loaded in the order given
    in the function call. Therefore, the latter will override the former
    if key overlap exists.
    Currently supported options are:
        - `root` (str), which determines the node that is considered as root.
        - `validate` (list), which gets a list of keys to check. If one of these
            keys is not present, `config.ConfigError` is raised.

    Arguments:
        *file_names (list[str]): Files to load.
        **options (dict): Configuration options. See above for supported
            options.

    Return:
        dict: Configuration.

    Raise:
        OSError: If some file does not exist.
        ConfigError: If key loading or validation fail.

    """
    unfolded_data = []
    for file_name in file_names:
        if not os.path.exists(file_name):
            raise OSError("Cannot find config file -> {}".format(file_name))
        try:
            with open(file_name) as input_obj:
                unfolded_data.extend(unfold_config(yaml.load(input_obj,
                                                             Loader=yamlordereddictloader.Loader)))
        except yaml.parser.ParserError as error:
            raise KeyError(str(error))
    data = fold_config(unfolded_data, OrderedDict)
    logger.debug('Loaded configuration -> %s', data)
    if 'root' in options:
        data_root = options['root']
        if data_root not in data:
            raise ConfigError("Root node not found in dataset -> {}".format(**data_root))
        data = data[data_root]
    if 'validate' in options:
        missing_keys = []
        data_keys = ['/'.join(key.split('/')[:entry_num+1])
                     for key, _ in unfolded_data
                     for entry_num in range(len(key.split('/')))]
        logger.debug("Validating against the following keys -> %s",
                     ', '.join(data_keys))
        for key in options['validate']:
            if key not in data_keys:
                missing_keys.append(key)
        if missing_keys:
            raise ConfigError("Failed validation: {} are missing".format(','.join(missing_keys)),
                              missing_keys)
    return data


def write_config(config, file_name):
    """Write configuration to file.

    Arguments:
        config (dict): Configuration file.
        file_name (str): Output file.

    """
    def represent_ordereddict(self, mapping, flow_style=None):
        """Dump an OrderedDict in YAML in the proper order.

        Modified from `yaml.representer.represent_mapping`.

        """
        tag = u'tag:yaml.org,2002:map'
        value = []
        node = yaml.representer.MappingNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        mapping = mapping.items()
        for item_key, item_value in mapping:
            node_key = self.represent_data(item_key)
            node_value = self.represent_data(item_value)
            if not (isinstance(node_key, yaml.representer.ScalarNode) and not node_key.style):
                best_style = False
            if not (isinstance(node_value, yaml.representer.ScalarNode) and not node_value.style):
                best_style = False
            value.append((node_key, node_value))
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node

    # Configure Dumper
    yaml.add_representer(OrderedDict, represent_ordereddict)
    # Dump
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

    Return:
        set: Keys that are different between the two configs,
            taking into account the values and the fact they are
            present in only one or the other.

    """
    return {key for key, _
            in set.symmetric_difference(set(unfold_config(config1)),
                                        set(unfold_config(config2)))}


# Helpers
def unfold_config(dictionary):
    """Convert a dictionary to a list of key, value pairs.

    Unfolding is done a la viewitems, but recursively.

    Arguments:
        dictionary (dict): Dictionary to update.

    Return:
        set: Unfolded dictionary.

    """
    output_list = []
    for key, val in dictionary.items():
        if isinstance(val, dict):
            for sub_key, sub_val in unfold_config(val):
                # convert non-hashable values to hashable (approximately)
                if isinstance(sub_val, list):
                    sub_val = tuple(sub_val)
                output_list.append(('{}/{}'.format(key, sub_key), sub_val))
        else:
            output_list.append((key, val))
    return output_list


def fold_config(unfolded_data, dict_class=dict):
    """Convert an unfolded dictionary (a la viewitems) back to a dictionary.

    Tuples are converted to lists. This reflects the inverted behaviour
    to :py:func:`unfold_config`.

    Note:
        If a key is specified more than once, the latest value is taken.

    Arguments:
        unfolded_data (iterable): Data to fold
        dict_class (class): Dictionary-like class used to fold the configuration.

    Return:
        dict: Folded configuration.

    """
    output_dict = dict_class()
    for key, value in unfolded_data:
        # convert tuples back to list
        if isinstance(value, tuple):
            value = list(value)
        current_level = output_dict
        for sub_key in key.split('/'):
            previous_level = current_level
            if sub_key not in current_level:
                current_level[sub_key] = dict_class()
            current_level = current_level[sub_key]
        # pylint: disable=W0631
        previous_level[sub_key] = value
    return output_dict


# Interpretation
def configure_parameter(name, title, parameter_config, external_vars=None):
    """Configure a parameter according to a configuration string.

    The configuration string consists in two parts. The first one
    consists in a letter that indicates the "action" to apply on the parameter,
    followed by the configuration of that action. There are several possibilities:
        * 'VAR' (or nothing) is used for parameters without constraints. If one configuration
        element is given, the parameter doesn't have limits. If three are given, the last two
        specify the low and upper limits. Parameter is set to not constant.
        * 'CONST' indicates a constant parameter. The following argument indicates
        at which value to fix it.
        * 'GAUSS' is used for a Gaussian-constrained parameter. The arguments of that
        Gaussian, ie, its mean and sigma, have to be given after the letter.
        * 'SHIFT' is used to perform a constant shift to a variable. The first value must be a
            shared variable, the second can be a number or a shared variable.
        * 'SCALE' is used to perform a constant scaling to a variable. The first value must be a
            shared variable, the second can be a number or a shared variable.

    In addition, wherever a variable value is expected one can use a 'fit_name:var_name' specification to
    load the value from a fit result. In the case of 'GAUSS', if no sigma is given, the Hesse error
    of the fit is taken as width of the Gaussian.

    Arguments:
        name (str): Name of the parameter.
        title (str): Title of the parameter.
        parameter_config (str): Parameter configuration.

    Return:
        tuple (ROOT.RooRealVar, ROOT.RooGaussian): Parameter and external constraint
            to apply to it (if requested by the configuration). If no constraint has been
            required, None is returned.

    Raise:
        KeyError: If the specified action is unknown.
        ValueError: If the action is badly configured.

    """
    import ROOT

    if external_vars is None:
        external_vars = {}
    constraint = None
    # Do something with it
    action_params = str(parameter_config).split()
    action = 'VAR' if not action_params[0].isalpha() else action_params.pop(0).upper()
    if action in ('VAR', 'CONST', 'GAUSS'):
        # Take numerical value or load from file
        value_error = None
        if ':' in action_params[0]:  # We want to load a fit result
            from analysis.fit.result import FitResult
            fit_name, var_name = action_params[0].split(':')
            result = FitResult().from_yaml_file(fit_name)
            try:
                value, value_error, _, _ = result.get_fit_parameter(var_name)
            except KeyError:
                value = result.get_const_parameter(var_name)
        else:
            try:
                value = float(action_params[0])
            except ValueError:

                print("error, action params[0]", action_params[0])

        parameter = ROOT.RooRealVar(name, title, value)
        if action == 'VAR':  # Free parameter, we specify its initial value
            parameter.setConstant(False)
            if len(action_params) > 1:
                try:
                    _, min_val, max_val = action_params
                except ValueError:
                    raise ValueError("Wrongly specified var (need to give 1 or 3 arguments) "
                                     "-> {}".format(action_params))
                parameter.setMin(float(min_val))
                parameter.setMax(float(max_val))
                parameter.setConstant(False)
        elif action == 'CONST':  # Fixed parameter
            parameter.setConstant(True)
        elif action == 'GAUSS':  # Gaussian constraint
            try:
                if len(action_params) == 1 and value_error is None:
                    raise ValueError
                elif len(action_params) == 2:
                    value_error = float(action_params[1])
                else:
                    raise ValueError
            except ValueError:
                raise ValueError("Wrongly specified Gaussian constraint -> {}".format(action_params))
            constraint = ROOT.RooGaussian(name + 'Constraint',
                                          name + 'Constraint',
                                          parameter,
                                          ROOT.RooFit.RooConst(value),
                                          ROOT.RooFit.RooConst(value_error))
            parameter.setConstant(False)
    elif action in ('SHIFT', 'SCALE'):
        # SHIFT @var val
        try:
            ref_var, second_var = action_params
        except ValueError:
            raise ValueError("Wrong number of arguments for {} -> {}".format(action, action_params))
        try:
            if ref_var.startswith('@'):
                ref_var = ref_var[1:]
            else:
                raise ValueError("The first value for a {} must be a reference.".format(action))
            ref_var, constraint = external_vars[ref_var]
            if second_var.startswith('@'):
                second_var = second_var[1:]
                second_var, const = external_vars[second_var]
                if not constraint:
                    constraint = const
                else:
                    raise NotImplementedError("Two constrained variables in SHIFT or SCALED are not allowed")
            elif ':' in second_var:
                from analysis.fit.result import FitResult
                fit_name, var_name = second_var.split(':')
                result = FitResult().from_yaml_file(fit_name)
                try:
                    value = result.get_fit_parameter(var_name)[0]
                except KeyError:
                    value = result.get_const_parameter(var_name)
                second_var = ROOT.RooFit.RooConst(value)
            else:
                if action in ('SHIFT', 'SCALE'):
                    second_var = ROOT.RooFit.RooConst(float(second_var))
        except KeyError as error:
            raise ValueError("Missing parameter definition -> {}".format(error))
        if action == 'SHIFT':
            parameter = ROOT.RooAddition(name, title, ROOT.RooArgList(ref_var, second_var))
        elif action == 'SCALE':
            parameter = ROOT.RooProduct(name, title, ROOT.RooArgList(ref_var, second_var))
    else:
        raise KeyError('Unknown action -> {}'.format(action))
    return parameter, constraint


def get_shared_vars(config, external_vars=None):
    """Configure shared variables for a given configuration.

    Shared variables are marked with the @-sign and configured with a string such as:

        @id/name/title/config

    where config follows the conventions of `configure_parameter`. In further occurences,
    `@id` is enough.

    Arguments:
        config (OrderedDict): Variable configuration from which to extract the
            shared variables.
        external_vars (dict, optional): Externally defined variables, which take precedence
            over the configuration. Defaults to None.

    Return:
        dict: Shared parameters build in the same parameter hierachy as the model they
            are included in.

    Raise:
        ValueError: If one of the parameters is badly configured.
        KeyError: If a parameter is refered to but never configured.

    """
    # Create shared vars
    parameter_configs = OrderedDict((config_element, config_value)
                                    for config_element, config_value in unfold_config(config)
                                    if isinstance(config_value, str) and '@' in config_value)
    # First build the shared var
    refs = {} if not external_vars else external_vars
    # Build shared parameters
    for config_element, config_value in parameter_configs.items():
        if not config_value.startswith('@'):
            continue
        split_element = config_value[1:].split('/')
        if len(split_element) == 4:
            ref_name, var_name, var_title, var_config = split_element
            if ref_name in refs:
                raise ValueError("Shared parameter defined twice -> {}".format(ref_name))
            var, constraint = configure_parameter(var_name, var_title, var_config, refs)
            var.setStringAttribute('shared', 'true')
            refs[ref_name] = (var, constraint)
        elif len(split_element) == 1:
            pass
        else:
            raise ValueError("Badly configured shared parameter -> {}: {}".format(config_element,
                                                                                  config_value))
    # Now replace the refs by the shared variables in a recursive defaultdict
    recurse_dict = lambda: defaultdict(recurse_dict)
    new_config = []
    for config_element, ref_val in parameter_configs.items():
        if ref_val.startswith('@'):
            new_config.append((config_element,
                               refs[ref_val.split('/')[0][1:]]))
        else:  # Composite parameter definition, such as SHIFT
            var_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))
            var, constraint = configure_parameter(var_name, var_name, ref_val, refs)
            var.setStringAttribute('tempName', 'true')
            new_config.append((config_element, (var, constraint)))
    return fold_config(new_config, recurse_dict)


# Exceptions
class ConfigError(Exception):
    """Error in loading configuration file."""
    def __init__(self, message, missing_keys=None):
        self.missing_keys = missing_keys if missing_keys else []
        super(ConfigError, self).__init__(message)

# EOF
