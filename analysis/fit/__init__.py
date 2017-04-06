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
from analysis.physics import get_physics_factory
from analysis.utils.config import configure_parameter
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


# Load PDFs
def load_pdfs(model):
    """Load the PDFs of the given model.

    This includes configuring parameters.

    Arguments:
        model (list[dict]): Model to load.

    Returns:
        tuple[dict, list]: Physics factories by name, and external constraints
            to apply to the fit (if any).

    Raises:
        KeyError: If some configuration data are missing.
        ValueError: If there is any problem in configuring the PDF factories.

    """
    # Get PDFs
    model_observables = None
    physics_factories = {}
    fit_parameters = {}
    constraints = []
    for name, element in model.items():
        pdfs = element['pdfs']
        try:
            physics_factory = get_physics_factory(pdfs)
        except KeyError:
            logger.error("Cannot find physics factory for %s",
                         ','.join(['%s:%s' % (obs, pdf['pdf'])
                                   for obs, pdf in pdfs.items()]))
            raise ValueError()
        physics_factories[name] = physics_factory
        observables = set(obs.GetName()
                          for obs in physics_factory.get_observables())
        if model_observables is None:
            model_observables = observables
        else:
            if model_observables != observables:
                logger.error("Mismatch in observables between PDFs.")
                raise KeyError()
        # Configure the variables
        for pdf in pdfs.values():
            fit_parameters = {param.GetName(): param
                              for param in physics_factory.get_fit_parameters()}
            # Rename parameters to param_name^{model_name} for easier visualization
            physics_factory.set_parameter_names({param_name: "%s^{%s}" % (param_name, name)
                                                 for param_name in fit_parameters})
            for parameter_name, param_config in pdf.get('parameter-constraints', {}).items():
                # Get the parameter
                try:
                    parameter = fit_parameters[parameter_name]
                except KeyError:
                    logger.error("Unknown parameter -> %s", parameter_name)
                    raise
                try:
                    constraint = configure_parameter(parameter, param_config)
                    if constraint:
                        constraints.append(constraint)
                except KeyError as error:
                    logger.error("Unknown parameter action -> %s", error)
                    raise
                except ValueError as error:
                    logger.error("Wrong parameter configuration -> %s", error)
                    raise
    return physics_factories, constraints


# EOF
