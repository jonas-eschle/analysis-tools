#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   11.01.2017
# =============================================================================
"""Generic analysis configuration."""

import os
from collections import defaultdict


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


# Initialize global variables
set_global_var('BASE_PATH',
               os.path.abspath(os.path.join(os.path.dirname(__file__))))
set_global_var('STYLE_PATH',
               os.path.join(get_global_var('BASE_PATH'),
                            'data_files', 'styles'))
# add_pdf_paths('pdfs')  # Setup {BASE_PATH}/pdfs as base dir for PDFs
set_global_var('PDF_PATHS', [])
set_global_var('FIT_STRATEGIES', {})
set_global_var('PHYSICS_FACTORIES', defaultdict(dict))
set_global_var('EFFICIENCY_MODELS', {})

# EOF
