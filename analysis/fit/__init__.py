#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   06.04.2017
# =============================================================================
"""Handle fitting procedures."""

import inspect

from analysis import get_global_var
from analysis.utils.logging_color import get_logger


logger = get_logger('analysis.fit')


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


# Get the fit strategy
def get_fit_strategy(name):
    """Get a fit strategy.

    Arguments:
        name (str): Name of the fit strategy.

    Returns:
        Callable: The fit function.

    Raises:
        KeyError: If the strategy is not registered.

    """
    return get_global_var('FIT_STRATEGIES')[name]


# Perform fit
# pylint: disable=R0913
def fit(factory, pdf_name, strategy, dataset, extended=True, minos=True, sumw2=False, verbose=False):
    """Fit a dataset.

    Raises:
        KeyError: If the fit strategy is not registered.
        ValueError: If there is a problem getting the PDF.

    """
    import ROOT

    fit_config = [ROOT.RooFit.Save(True),
                  ROOT.RooFit.Extended(extended),
                  ROOT.RooFit.Minos(minos),
                  ROOT.RooFit.SumW2Error(sumw2),
                  ROOT.RooFit.PrintLevel(2 if verbose else -1)]
    constraints = factory.get_constraints()
    if constraints.getSize():
        fit_config.append(ROOT.RooFit.ExternalConstraints(constraints))
    try:
        fit_func = get_fit_strategy(strategy)
    except KeyError:
        raise KeyError("Unknown fit strategy -> %s" % strategy)
    try:
        model = factory.get_extended_pdf(pdf_name, pdf_name) \
            if extended \
            else factory.get_pdf(pdf_name, pdf_name)
    except ValueError as error:
        logger.error("Problem getting the PDF -> %s", error)
        raise
    return fit_func(model, dataset, fit_config)


# EOF
