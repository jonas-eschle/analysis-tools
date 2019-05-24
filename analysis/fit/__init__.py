#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   06.04.2017
# =============================================================================
"""Handle fitting procedures."""
from __future__ import print_function, division, absolute_import

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
        name (str): Name of the strategy.
        fit_function (Callable): Fit function.

    Return:
        int: Number of registered fit strategies.

    Raise:
        ValueError: If the fit function doesn't have the correct number of parameters.

    """
    try:  # PY3
        fit_function_args = inspect.getfullargspec(fit_function).args
    except AttributeError:  # PY2
        fit_function_args = inspect.getargspec(fit_function).args
    if len(fit_function_args) != 3:
        raise ValueError("The strategy function needs to have 3 arguments")
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

    Return:
        Callable: The fit function.

    Raise:
        KeyError: If the strategy is not registered.

    """
    return get_global_var('FIT_STRATEGIES')[name]


# Perform fit
# pylint: disable=R0913
def fit(factory, pdf_name, strategy, dataset, verbose=False, **kwargs):
    """Fit a dataset.

    Raise:
        KeyError: If the fit strategy is not registered.
        ValueError: If there is a problem getting the PDF.

    """
    import ROOT

    # Check the match between dataset and factory
    dataset_event = dataset.get()
    for obs in factory.get_observables():
        dataset_obs = dataset_event[obs.GetName()]
        if (obs.getMin(), obs.getMax()) != (dataset_obs.getMin(), dataset_obs.getMax()):
            logger.warning("Mismatching ranges between PDF and dataset for observable %s, correcting...",
                           obs.GetName())
            dataset_obs.setMin(obs.getMin())
            dataset_obs.setMax(obs.getMax())
    fit_config = [ROOT.RooFit.Save(True),
                  ROOT.RooFit.PrintLevel(2 if verbose else kwargs.get('PrintLevel', -1))]
    kwargs.setdefault('Range', 'Full')
    for command, val in kwargs.items():
        if command == 'Minos' and dataset.isWeighted():
            # Explicitly disabled Minos
            val = False
        else:
            roo_cmd = getattr(ROOT.RooFit, command, None)
        if not roo_cmd:
            logger.warning("Specified unknown RooArgCmd %s", command)
            continue
        fit_config.append(roo_cmd(val))
    if dataset.isWeighted():
        fit_config.append(ROOT.RooFit.SumW2Error(True))
    constraints = factory.get_constraints()
    if constraints.getSize():
        fit_config.append(ROOT.RooFit.ExternalConstraints(constraints))
    try:
        fit_func = get_fit_strategy(strategy)
    except KeyError:
        raise KeyError("Unknown fit strategy -> {}".format(strategy))
    print('\n\n\n\n\n{}\n\n\n\n\n'.format(fit_config))
    try:
        model = factory.get_extended_pdf(pdf_name, pdf_name) \
            if factory.is_extended() \
            else factory.get_pdf(pdf_name, pdf_name)
    except ValueError as error:
        logger.error("Problem getting the PDF -> %s", error)
        raise
    if kwargs.get('Extended', False) != factory.is_extended():
        logger.warning("Requested fit with Extended=%s fit on %s extended PDF. Check this is what you want.",
                       kwargs.get('Extended', False),
                       'an ' if factory.is_extended() else 'a non-')
    return fit_func(model, dataset, fit_config)

# EOF
