#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   random.py
# @author Jonas Eschle "Mayou36" (jonas.eschle@cern.ch)
# @date   07.11.2017
# =============================================================================
"""Custom exceptions."""
from __future__ import print_function, division, absolute_import


class ConfigError(Exception):
    """Error in loading configuration file."""

    def __init__(self, message, missing_keys=None):
        self.missing_keys = missing_keys if missing_keys else []
        super(ConfigError, self).__init__(message)


class DataError(Exception):
    """Error in handling data."""

    def __init__(self, message):
        super(DataError, self).__init__(message)


class InvalidRequestError(Exception):
    """Invalid request made."""

    def __init__(self, message):
        super(InvalidRequestError, self).__init__(message)


class FactoryError(Exception):
    """Error inside a Factory."""

    def __init__(self, message):
        super(FactoryError, self).__init__(message)


class NotInitializedError(Exception):
    """Use when an object has not been initialized."""
