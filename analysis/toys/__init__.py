#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.03.2017
# =============================================================================
"""Toy scripts."""

import inspect

from analysis import get_global_var
from analysis.utils.logging_color import get_logger


logger = get_logger('analysis.toys')


def register_fit_strategy(name, fit_function):
    """Register a toy fitting strategy.

    The fit function gets three parameters:
        - The PDF model
        - The dataset
        - The fit configuration list

    Arguments:
        namefit_function: Name of the strategy.
        function (Callable): Fit function.

    Returns:
        int: Number of registered fit strategies.

    Raises:
        ValueError: If the fit function doesn't have the correct number of parameters.

    """
    if len(inspect.getargspec(fit_function).args) != 3:
        raise ValueError("The stragey function needs to have 3 arguments")
    logger.debug("Registering %s fitting strategy", name)
    get_global_var('FIT_STRATEGIES').update({name: fit_function})
    return len(get_global_var('FIT_STRATEGIES'))


# Register simple fit strategy
register_fit_strategy('simple',
                      lambda model, dataset, fit_config: model.fitTo(dataset, *fit_config))

# EOF
