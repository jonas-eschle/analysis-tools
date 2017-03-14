#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   __init__.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   11.01.2017
# =============================================================================
"""Common tools."""

import os

import ROOT

from analysis import get_global_var

from .root import load_library as _load_library
from .logging_color import get_logger


PDF_PATHS = get_global_var('PDF_PATHS')

_logger = get_logger('analysis.utils.pdf')


def load_pdf_by_name(name):
    """Load the given PDF using its name.

    It's compiled if needed.

    Arguments:
        name (str): Name of the PDF to load.

    Returns:
        `ROOT.RooAbsPdf`: RooFit PDF object.

    Raises:
        OSError: If the .cc file corresponding to `name` cannot be found.

    """
    try:
        _load_library(name, PDF_PATHS)
    except OSError:
        raise OSError("Don't know this PDF! -> %s" % name)
    return getattr(ROOT, os.path.splitext(os.path.split(name)[1])[0])


# EOF
