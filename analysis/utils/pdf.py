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


_logger = get_logger('analysis.utils.pdf')


def add_pdf_paths(*paths):
    """Add path to the global 'PDF_PATHS' variable if not already there.

    The inserted paths take preference.

    Note:
        If any of the paths is relative, it is built in relative to
        `BASE_PATH`.

    Arguments:
        *paths (list): List of paths to append.

    Returns:
        list: Updated PDF paths.

    """
    base_path = get_global_var('BASE_PATH')
    for path in reversed(paths):
        if not os.path.isabs(path):
            path = os.path.abspath(os.path.join(base_path, path))
        if path not in get_global_var('PDF_PATHS'):
            _logger.debug("Adding %s to PDF_PATHS", path)
            get_global_var('PDF_PATHS').insert(0, path)
    return get_global_var('PDF_PATHS')


# Default PDF path
add_pdf_paths('pdfs')


def load_pdf_by_name(name, use_mathmore=False):
    """Load the given PDF using its name.

    It's compiled if needed.

    Arguments:
        name (str): Name of the PDF to load.
        use_mathmore (bool, optional): Load libMathMore before compiling.
            Defaults to False.

    Returns:
        `ROOT.RooAbsPdf`: RooFit PDF object.

    Raises:
        OSError: If the .cc file corresponding to `name` cannot be found.

    """
    try:
        _load_library(name,
                      lib_dirs=get_global_var('PDF_PATHS'),
                      use_mathmore=use_mathmore)
    except OSError:
        raise OSError("Don't know this PDF! -> %s" % name)
    return getattr(ROOT, os.path.splitext(os.path.split(name)[1])[0])


# EOF
