#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   backports.py
# @author Jonas Eschle "Mayou36" (jonas.eschle@cern.ch)
# @date   04.12.2017
# =============================================================================
"""Manual backports from Python 3."""
from __future__ import print_function, division, absolute_import

import sys

if sys.version_info[0] < 3:

    class FileNotFoundError(OSError):
        """ File not found. """

        def __init__(self, message, *args, **kwargs):
            try:
                message = args[1]
            except IndexError:
                pass
            message = " *unstable message, do not rely on it* " + str(message)
            super(FileNotFoundError, self).__init__(message)


else:
    from builtins import FileNotFoundError
