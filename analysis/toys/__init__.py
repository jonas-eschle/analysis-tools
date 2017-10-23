#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.03.2017
# =============================================================================
"""Toy scripts."""
from __future__ import print_function, division, absolute_import

from analysis import get_global_var
from analysis.utils.logging_color import get_logger

from .systematics import SYSTEMATIC_TOYS as _SYSTEMATIC_TOYS

logger = get_logger('analysis.toys')


def register_systematic(name, syst_class):
    """Register a systematic toy generator.

    Systematics are registered in the `TOY_SYSTEMATICS` global variable.

    Arguments:
        name (str): Name of the systematic.
        syst_class (SystematicToys): SystematicToys generator class to register.

    Return:
        int: Number of registered systematics.

    Raise:
        ValueError: If `syst_class` is not of the correct type.

    """
    from analysis.toys.systematics import SystematicToys
    logger.debug("Registering %s systematic generator", name)
    if not issubclass(syst_class, SystematicToys):
        raise ValueError("Wrong class type -> {}".format(type(syst_class)))
    get_global_var('TOY_SYSTEMATICS').update({name: syst_class})
    return len(get_global_var('TOY_SYSTEMATICS'))


# Register our models
for syst_name, class_ in _SYSTEMATIC_TOYS.items():
    register_systematic(syst_name, class_)


def get_systematic(syst_config):
    """Load systematic toy generator.

    The systematic type is specified through the `type` key.

    Arguments:
        syst_config (dict): Configuration of the systematic toy.

    Return:
        SystematicToys class

    Raise:
        KeyError: If the systematic type is unknown.

    """
    return get_global_var('TOY_SYSTEMATICS')[syst_config['type']]


# EOF
