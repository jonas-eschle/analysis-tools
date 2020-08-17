#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   decorators.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   16.11.2017
# =============================================================================
"""Useful decorators."""
from __future__ import print_function, division, absolute_import


# pylint: disable=R0903,C0103
class memoize(object):
    """Memoize the creation of class instances."""

    def __init__(self, cls):
        """Initialize the decorator.

        Pay special attention to static methods.

        """
        self.cls = cls
        cls.instances = {}
        self.__dict__.update(cls.__dict__)

        # This bit allows staticmethods to work as you would expect.
        for attr, val in cls.__dict__.items():
            if isinstance(val, staticmethod):
                self.__dict__[attr] = val.__func__

    def __call__(self, *args, **kwargs):
        """Create class instance.

        Instances are memoized according to their init arguments, which are converted
        to string and used as keys.

        """
        key = '{}//{}'.format('//'.join(map(str, args)),
                              '//'.join('{}:{}'.format(str(key), str(val))
                                        for key, val in kwargs.items()))
        if key not in self.cls.instances:
            self.cls.instances[key] = self.cls(*args, **kwargs)
        return self.cls.instances[key]

# EOF
