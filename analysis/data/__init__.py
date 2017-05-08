#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   10.04.2017
# =============================================================================
"""Manage datasets."""

import os

from analysis import get_global_var
from analysis.utils.config import load_config
from analysis.utils.logging_color import get_logger
import analysis.utils.paths as paths


logger = get_logger('analysis.data')


def register_file_type(extension, file_type):
    """Register a file type with a given extension.

    Returns:
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


def load_data(config_file):
    """Load from file.

    Returns:
        object: Data object.

    Raises:
        analysis.utils.config.ConfigError: If there is a problem with the efficiency model.

    """
    config_file = os.path.abspath(config_file)
    return get_data(load_config(config_file))


def get_data(data_config, **kwargs):
    """Get data.

    Detects the input file extension and uses the proper loader.

    The required configuration keys are:
        + `source`: Input source. If `source-type` is specified, the file name will
            be obtained executing `get_{source-type}_path`, otherwise `source` is
            treated as a file name.
        + `tree`: Tree within the file.
        + 'output-format': Type of data we want. Currently `root` or `pandas`.

    Raises:
        AttributeError: If the specified source type is unknown.
        KeyError: If the input file extension is not recognized.
        OSError: If the input file can't be found.
        ValueError: If the requested output format is not available for the input.

    """
    import analysis.data.loaders as _loaders
    if isinstance(data_config, list):
        from analysis.data.mergers import merge
        return merge([get_data(data) for data in data_config], **kwargs)
    # Check the configuration
    for key in ('source', 'tree', 'output-format'):
        if key not in data_config:
            raise KeyError("Bad data configuration -> '%s' key is missing" % key)
    source_name = data_config.pop('source')
    try:
        source_type = data_config.pop('source-type', None)
        file_name = source_name if not source_type \
            else getattr(paths, 'get_%s_path' % source_type)(source_name)
        if not os.path.exists(file_name):
            raise OSError("Cannot find input file -> %s" % file_name)
    except AttributeError:
        raise AttributeError("Unknown source type -> %s" % source_type)
    tree_name = data_config.pop('tree')
    output_format = data_config.pop('output-format').lower()
    # Optional: output-type, cuts, branches
    input_ext = os.path.splitext(file_name)[1]
    try:
        input_type = get_global_var('FILE_TYPES')[input_ext]
    except KeyError:
        raise KeyError("Unknown file extension -> %s. Cannot load file." % input_ext)
    try:
        get_data_func = getattr(_loaders,
                                'get_%s_from_%s_file' % (output_format, input_type))
    except AttributeError:
        raise ValueError("Output format unavailable for input file"
                         "with extension %s -> %s" % (input_ext, output_format))
    return get_data_func(file_name, tree_name, data_config)


# EOF
