#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   11.01.2017
# =============================================================================
"""Common utilities."""
from __future__ import print_function, division, absolute_import

import inspect

from analysis import get_global_var
from analysis.utils.logging_color import get_logger
from analysis.utils import actions as _actions

logger = get_logger('analysis.utils')


def register_config_action(name, action_function):
    """Register a config action keyword.

    The action gets four parameters:
        - The name of the parameter
        - The title of the parameter
        - The parameter configuration
        - The list of shared vars.

    Arguments:
        name (str): Name of the action.
        action_function (Callable): Parameter config action.

    Return:
        int: Number of registered config actions.

    Raise:
        ValueError: If the configuration action function doesn't have the correct number of parameters.

    """
    try:  # PY3
        action_function_args = inspect.getfullargspec(action_function).args
    except AttributeError:  # PY2
        action_function_args = inspect.getargspec(action_function).args
    if len(action_function_args) != 4 and not 'BLINDRATIO' in action_function:
        raise ValueError("The action configuration function needs to have 4 arguments")
    logger.debug("Registering %s parameter configuration keyword", name)
    get_global_var('PARAMETER_KEYWORDS').update({name: action_function})
    return len(get_global_var('PARAMETER_KEYWORDS'))


for func_name, action_func in inspect.getmembers(_actions, inspect.isfunction):
    if func_name.startswith('action_'):
        keyword = func_name[len('action_'):]  # stripping of 'action_'
        register_config_action(keyword, action_func)


# Get the fit strategy
def get_config_action(name):
    """Get a configuration action.

    Arguments:
        name (str): Name of the configuration keyword.

    Return:
        Callable: The parameter configuration function.

    Raise:
        KeyError: If the keyword is not registered.

    """
    return get_global_var('PARAMETER_KEYWORDS')[name]


# EOF
