#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   config.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.01.2017
# =============================================================================
"""Configuration files."""

from __future__ import print_function, division, absolute_import

import copy
import os
import random
import string

from collections import OrderedDict, defaultdict

import yaml
import yamlloader

from analysis.utils.exceptions import ConfigError
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

    Additionally, several commands are available to modify the configurations:
        - The `load` key can be used to load other config files from the
            config file. The value of this key can have two formats:

            + `file_name:key` inserts the contents of `key` in `file_name` at the same
                level as the `load` entry. `file_name` is relative to the lowest common
                denominator of `file_names`.
            + `path_func:name:key` inserts the contents `key` in the file obtained by the
                `get_{path_func}_path(name)` call at the same level as the `load` entry.
        - The `modify` command can be used to modify a previously loaded key/value pair.
            It has the format `key: value` and replaces `key` at its same level by the value
            given by `value`. For more complete examples and documentation, see the README.
        - The `globals` key can be used to define global variables. Access is via a value
          written as "globals.path_to.myvar" with a configuration like:
          {globals: {path_to: {myvar: myval}},....}. This will replace it with `myval`.

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
                                                             Loader=yamlloader.ordereddict.CLoader)))
        except yaml.parser.ParserError as error:
            raise KeyError(str(error))
    # Load required data
    unfolded_data_expanded = []
    root_prev_load = None
    for key, val in unfolded_data:
        command = key.split('/')[-1]
        if command == 'load':  # An input requirement has been made
            split_val = val.split(":")
            if len(split_val) == 2:  # file_name:key format
                file_name_result, required_key = split_val
                if not os.path.isabs(file_name_result):
                    if len(file_names) == 1:
                        file_name_result = os.path.join(os.path.split(file_names[0])[0], file_name_result)
                    else:
                        file_name_result = os.path.join(os.path.commonprefix(*file_names), file_name_result)
            elif len(split_val) == 3:  # path_func:name:key format
                path_name, name, required_key = split_val
                import analysis.utils.paths as _paths
                try:
                    path_func = getattr(_paths, 'get_{}_path'.format(path_name))
                except AttributeError:
                    raise ConfigError("Unknown path getter type -> {}".format(path_name))
                file_name_result = path_func(name)
            else:
                raise ConfigError("Malformed 'load' key")
            try:
                root = key.rsplit('/load')[0]
                for new_key, new_val in unfold_config(load_config(file_name_result, root=required_key)):
                    unfolded_data_expanded.append(('{}/{}'.format(root, new_key), new_val))
            except Exception:
                logger.error("Error loading required data in %s", required_key)
                raise
            else:
                root_prev_load = root
        elif root_prev_load and key.startswith(root_prev_load):  # we have to handle it *somehow*
            relative_key = key.split(root_prev_load + '/', 1)[1]  # remove root
            if not relative_key.startswith('modify/'):
                logger.error("Key % cannot be used without 'modify' if 'load' came before.", key)
                raise ConfigError("Loaded pdf with 'load' can *only* be modified by using 'modify'.")

            key_to_replace = '{}/{}'.format(root_prev_load, relative_key.split('modify/', 1)[1])
            try:
                key_index = [key for key, _ in unfolded_data_expanded].index(key_to_replace)
            except IndexError:
                logger.error("Cannot find key to modify -> %s", key_to_replace)
                raise ConfigError("Malformed 'modify' key")
            unfolded_data_expanded[key_index] = (key_to_replace, val)
        else:
            root_prev_load = None  # reset, there was no 'load'
            unfolded_data_expanded.append((key, val))
    # Fold back
    data = fold_config(unfolded_data_expanded, OrderedDict)

    # Replace globals
    data = replace_globals(data)

    logger.debug('Loaded configuration -> %s', data)
    data_root = options.get('root', '')
    if data_root:
        for root_node in data_root.split('/'):
            try:
                data = data[root_node]
            except KeyError:
                raise ConfigError("Root node {} of {} not found in dataset".format(root_node, data_root))
    if 'validate' in options:
        missing_keys = []
        data_keys = ['/'.join(key.split('/')[:entry_num+1])
                     for key, _ in unfolded_data
                     for entry_num in range(len(key.split('/')))]
        logger.debug("Validating against the following keys -> %s",
                     ', '.join(data_keys))
        for key in options['validate']:
            key = os.path.join(data_root, key)
            if key not in data_keys:
                missing_keys.append(key)
        if missing_keys:
            raise ConfigError("Failed validation: {} are missing".format(','.join(missing_keys)),
                              missing_keys)
    return data


def replace_globals(folded_data):
    """Replace values referencing to global, remove global.

    Args:
        folded_data (dict): The folded config containing

    Returns:
        OrderedDict : *folded_data* with the global keyword removed and
            every value containing the global keyword replaced by the value.

    """
    GLOBALS_KEYWORD = 'globals'
    SEP = '.'
    folded_data = folded_data.copy()  # do not mutate arguments

    # gather globals
    yaml_globals = folded_data.pop(GLOBALS_KEYWORD, {})
    unfolded_data = unfold_config(folded_data)

    # replace globals
    for key, val in unfolded_data:
        if isinstance(val, str) and val.startswith(GLOBALS_KEYWORD + SEP):
            glob_keys = val.split(SEP)[1:]  # remove identifier
            yaml_global = yaml_globals
            try:
                for glob_key in glob_keys:
                    yaml_global = yaml_global[glob_key]
            except KeyError:
                raise ConfigError(
                    "Invalid global reference '{}': value {key} not found".format(val, key=key))
            unfolded_data.append((key, yaml_global))

    return fold_config(unfolded_data, OrderedDict)


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
        * 'BLIND' covers the actual parameter by altering its value in an unknown way. The first
            value must be a shared variable whereas the following are a string and two floats.
            They represent a randomization string, a mean and a width (both used for the
            randomization of the value as well).

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
    from analysis.utils import get_config_action

    if external_vars is None:
        external_vars = {}
    # Do something with it
    action_params = str(parameter_config).split()
    action = 'VAR' if not action_params[0].isalpha() else action_params.pop(0).upper()
    try:
        return get_config_action(name, title, action, action_params, external_vars)
    except KeyError:
        raise KeyError('Unknown action -> {}'.format(action))


def get_shared_vars(config, external_vars=None):
    """Configure shared variables for a given configuration.

    Shared variables are marked with the @-sign and configured with a string such as:

        @id/name/title/config

    where config follows the conventions of `configure_parameter`. In further occurrences,
    `@id` is enough.

    Arguments:
        config (OrderedDict): Variable configuration from which to extract the
            shared variables.
        external_vars (dict, optional): Externally defined variables, which take precedence
            over the configuration. Defaults to None.

    Return:
        dict: Shared parameters build in the same parameter hierarchy as the model they
            are included in.

    Raise:
        ValueError: If one of the parameters is badly configured.
        KeyError: If a parameter is referred to but never configured.

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


def recursive_dict_copy(x, to_copy=None):
    """*Deepcopy* all dicts and *to_copy* elements inside *x*.

    A selective *deepcopy* of a dict where only the selected elements (*to_copy* and
    dict/OrderedDict) are copied, the others remain as a reference. This prevents that
    additional objects (like numpy arrays) are created while the dictionary and it's
    sub-dictionaries are fully copied and newly created.

    If x is an *ordereddict* instead of a dict, the returned object will also be an OrderedDict.

    Args:
        x (dict): The dictionary to be copied.
        to_copy (cls or list/tuple/set of cls): if any element is an instance of cls,
            it is copied (shallow). Otherwise a reference will remain in the new dict pointing
            to the old dicts object.
    """
    iterables = (list, tuple, set)
    dicts = (dict, OrderedDict)
    if not isinstance(x, dicts):
        raise TypeError("{} has to be of type {} but is {}".format(x, dicts, type(x)))
    if not (isinstance(to_copy, iterables) and len(to_copy) > 0):
        to_copy = (to_copy,)

    to_copy = set(to_copy)
    new_dict = copy.copy(x)

    # iterate and call recursive
    for key, val in x.items():
        if isinstance(val, dicts):
            new_dict[key] = recursive_dict_copy(x=val, to_copy=to_copy)
        elif not (len(to_copy) == 1 and None in to_copy) and isinstance(val, tuple(to_copy)):
            new_dict[key] = copy.copy(val)

    return new_dict






# EOF
