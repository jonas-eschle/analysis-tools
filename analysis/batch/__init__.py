#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   31.05.2017
# =============================================================================
"""Batch managing utils."""
from __future__ import print_function, division, absolute_import


def get_batch_system(name=None):
    """Get the batch system, optionally detecting it from the system.

    If two batch systems are present, the priority is defined by the order of
    the `analysis.batch.batch_system.BATCH_SYSTEMS` OrderedDict.

    Arguments:
        name (str, optional): Name of the batch system to get. Defaults to
            None, in which case the batch system detection is activated.

    Return:
        str: Detected batch system.

    Raise:
        ValueError: If no batch system was detected.

    """
    from analysis.batch.batch_system import BATCH_SYSTEMS
    if name:
        batch_system = BATCH_SYSTEMS.get(name, None)
        if batch_system:
            return batch_system
    else:
        for batch_system in BATCH_SYSTEMS.values():
            if batch_system.is_available():
                return batch_system
    raise ValueError()


def get_job_id():
    """Get job ID from the environment.

    Return:
        str: JobID, empty if it's a local job.

    """
    from analysis.batch.batch_system import BATCH_SYSTEMS
    for batch_system in BATCH_SYSTEMS.values():
        job_id = batch_system.get_job_id()
        if job_id:
            return job_id
    return ''


# EOF
