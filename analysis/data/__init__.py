#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   10.04.2017
# =============================================================================
"""Manage datasets."""
from __future__ import print_function, division, absolute_import

import os

from analysis import get_global_var
from analysis.utils.config import load_config
from analysis.utils.logging_color import get_logger
import analysis.utils.paths as paths

logger = get_logger('analysis.data')


def register_file_type(extension, file_type):
    """Register a file type with a given extension.

    Return:
        int: Number of extensions registered with that particular file type.

    """
    if not extension.startswith('.'):
        extension = "." + extension
    logger.debug("Registering file type for extension %s -> %s", extension, file_type)
    get_global_var('FILE_TYPES').update({extension: file_type})
    return sum(1
               for f_type in get_global_var('FILE_TYPES').values()
               if f_type == file_type)


# Register
register_file_type('h5', 'pandas')
register_file_type('hdf', 'pandas')
register_file_type('root', 'root')


def load_data(config_file, key=None, **kwargs):
    """Load from file.

    Arguments:
        config_file (str): Name of the configuration file.
        key (str, optional): Key to load in the configuration file. If none is
            given, the root of the YAML file will be used as configuration.
        **kwargs (dict): Dictionary to override keys from the dictionary.

    Return:
        object: Data object.

    Raise:
        OSError: If the config file cannot be loaded.
        ConfigError: If the validation of the ConfigFile fails.

    """
    config_file = os.path.abspath(config_file)
    if not os.path.exists(config_file):
        raise OSError("Cannot find config file -> {}".format(config_file))
    return get_data(load_config(config_file,
                                root=key,
                                validate=['source', 'tree', 'output-format']),
                    **kwargs)


def get_data(data_config, **kwargs):
    """Get data.

    Detects the input file extension and uses the proper loader.

    The required configuration keys are:
        + `source`: Input source. If `source-type` is specified, the file name will
            be obtained executing `get_{source-type}_path`, otherwise `source` is
            treated as a file name.
        + `tree`: Tree within the file.
        + `output-format`: Type of data we want. Currently `root` or `pandas`.

    Optional config keys:
        + `input-type`: type of input, in case the extension has not been registered.

    Raise:
        AttributeError: If the specified source type is unknown.
        KeyError: If the input file extension is not recognized.
        OSError: If the input file can't be found.
        ValueError: If the requested output format is not available for the input.

    """
    import analysis.data.loaders as _loaders
    # Do we need to merge?
    if isinstance(data_config, list):
        from analysis.data.mergers import merge
        logger.debug("Multiple datasets specified. Merging...")
        return merge([get_data(data) for data in data_config], **kwargs)
    # Merge data_config and keyword arguments
    data_config.update(kwargs)
    # Check the configuration
    for key in ('source', 'tree', 'output-format'):
        if key not in data_config:
            raise KeyError("Bad data configuration -> '{}' key is missing".format(key))
    source_name = data_config.pop('source')
    try:
        source_type = data_config.pop('source-type', None)
        file_name = source_name if not source_type \
            else getattr(paths, 'get_{}_path'.format(source_type))(source_name)
        if not os.path.exists(file_name):
            raise OSError("Cannot find input file -> {}".format(file_name))
    except AttributeError:
        raise AttributeError("Unknown source type -> {}".format(source_type))
    tree_name = data_config.pop('tree')
    output_format = data_config.pop('output-format').lower()
    # Optional: output-type, cuts, branches
    input_ext = os.path.splitext(file_name)[1]
    try:
        input_type = data_config.get('input-type')
        if not input_type:
            input_type = get_global_var('FILE_TYPES')[input_ext]
    except KeyError:
        raise KeyError("Unknown file extension -> {}. Cannot load file.".format(input_ext))
    try:
        get_data_func = getattr(_loaders,
                                'get_{}_from_{}_file'.format(output_format, input_type))
    except AttributeError:
        raise ValueError("Output format unavailable for input file"
                         "with extension {} -> {}".format(input_ext, output_format))
    logger.debug("Loading data file -> %s:%s", file_name, tree_name)
    return get_data_func(file_name, tree_name, data_config)

# EOF
