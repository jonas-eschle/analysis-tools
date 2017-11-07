#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   random.py
# @author Jonas Eschle "Mayou36" (jonas.eschle@cern.ch)
# @date   07.11.2017
# =============================================================================
"""Random generation tools."""
from __future__ import print_function, division, absolute_import

import sys, os


def get_urandom_int(length):
    """Generate a truly random number.

    Can be used to initialize a random generator *truly* randomly.

    Args:
        length (int): Length of binary generated number in bytes
        (e.g. 4 -> int, 8 -> long), the returned 10-base number
        will have less digits

    Returns:
        int: The random number in 10-base

    """
    try:
        rand_int = int.from_bytes(os.urandom(100), sys.byteorder)
    except AttributeError:  # py2
        rand_int = int(os.urandom(10).encode('hex'), 16)
    return rand_int

