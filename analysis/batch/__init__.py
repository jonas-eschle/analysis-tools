#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   31.05.2017
# =============================================================================
"""Batch managing utils."""


def get_batch_system():
    """Detect and get the batch system.

    If two batch systems are present, the priority is defined by the order of
    the `analysis.batch.batch_system.BATCH_SYSTEMS` OrderedDict.

    Returns:
        str: Detected batch system.

    Raises:
        ValueError: If no batch system was detected.

    """
    from analysis.batch.batch_system import BATCH_SYSTEMS
    for batch_system in BATCH_SYSTEMS.values():
        if batch_system.is_available:
            return batch_system
    raise ValueError()

# EOF
