#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   11.01.2017
# =============================================================================
"""Generic analysis configuration."""

import os


__GLOBAL_VARIABLES = {}


# Functions to modify and access the global variables
def get_global_var(name, default=None):
    """Get a global variable.

    Arguments:
        name (str): Name of the variable.
        default (object, optional): Value to return if the global variable
            is not defined. Defaults to `None`.

    Returns:
        object: Value of the global variable.

    """
    return __GLOBAL_VARIABLES.get(name, default)


def set_global_var(name, value):
    """Set value of a global variable.

    Arguments:
        name (str): Name of the variable.
        value (object): Value to assign to the global variable.

    Returns:
        object: Value of the global variable.

    """
    __GLOBAL_VARIABLES[name] = value
    return __GLOBAL_VARIABLES[name]


def add_pdf_paths(*paths):
    """Add path to the global 'PDF_PATHS' variable if not already there.

    The inserted paths take preference.

    Note:
        If any of the paths is relative, it is built in relative to
        `BASE_PATH`.

    Arguments:
        *paths (list): List of paths to append.

    Returns:
        list: Updated PDF paths.

    """
    base_path = __GLOBAL_VARIABLES['BASE_PATH']
    if 'PDF_PATHS' not in __GLOBAL_VARIABLES:
        __GLOBAL_VARIABLES['PDF_PATHS'] = []
    for path in reversed(paths):
        if not os.path.isabs(path):
            path = os.path.abspath(os.path.join(base_path, path))
        if path not in __GLOBAL_VARIABLES['PDF_PATHS']:
            __GLOBAL_VARIABLES['PDF_PATHS'].insert(0, path)
    return __GLOBAL_VARIABLES['PDF_PATHS']


# Configure global variables
set_global_var('BASE_PATH',
               os.path.abspath(os.path.join(os.path.dirname(__file__))))
add_pdf_paths('pdfs')  # Setup {BASE_PATH}/pdfs as base dir for PDFs
set_global_var('FIT_STRATEGIES',
               {'simple': lambda model, dataset, fit_config: model.fitTo(dataset, *fit_config)})

# EOF
