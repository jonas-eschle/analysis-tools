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
from .randomizers import TOY_RANDOMIZERS as _TOY_RANDOMIZERS

logger = get_logger('analysis.toys')


def register_toy_randomizer(name, rand_class):
    """Register a randomized toy generator.

    Randomizers are registered in the `TOY_RANDOMIZERS` global variable.

    Arguments:
        name (str): Name of the randomizer.
        rand_class (ToyRandomizer): Randomizer class to register.

    Return:
        int: Number of registered randomizers.

    Raise:
        ValueError: If `rand_class` is not of the correct type.

    """
    from analysis.toys.randomizers import ToyRandomizer
    logger.debug("Registering %s toy randomizer", name)
    if not issubclass(rand_class, ToyRandomizer):
        raise ValueError("Wrong class type -> {}".format(type(rand_class)))
    get_global_var('TOY_RANDOMIZERS').update({name: rand_class})
    return len(get_global_var('TOY_RANDOMIZERS'))


# Register our models
for rand_name, class_ in _TOY_RANDOMIZERS.items():
    register_toy_randomizer(rand_name, class_)


def get_randomizer(rand_config):
    """Load randomized toy generator.

    The randomizer type is specified through the `type` key.

    Arguments:
        rand_config (dict): Configuration of toy randomizer.

    Return:
        ToyRandomizer class

    Raise:
        KeyError: If the randomizer type is unknown.

    """
    return get_global_var('TOY_RANDOMIZERS')[rand_config['type']]

# EOF
