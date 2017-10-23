#!/usr/bin/env python
# =============================================================================
# @file   logging_color.py
# @author C. Marin Benito (carla.marin.benito@cern.ch)
# @date   16.03.2016
# =============================================================================
"""Configure the logging.

These functions configures a logger using logging and colorlog
and returns the logger for further usage
By default, time, name of the logger and message with the default
colorlog color scheme are printed.
The threshold level for displaying messages and the format of the
logger can be configured with the lvl and format arguments

"""
from __future__ import print_function, division, absolute_import

import logging
import colorlog


def get_logger(name, lvl=logging.NOTSET, format_=None):
    """Configure logging.

    Arguments:
        name (str): Name of the logger.
        lvl (int, optional): Logging level. Defaults to
            `logging.NOTSET`.
        format_ (str): Logger formatting string

    Return:
        `logging.Logger`: The requested logger.

    """
    if not format_:
        format_ = ("%(asctime)s - %(name)s | "
                   "%(log_color)s%(levelname)-8s%(reset)s | "
                   "%(log_color)s%(message)s%(reset)s")

    if not len(logging.root.handlers):
        formatter = colorlog.ColoredFormatter(format_)
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        logging.root.addHandler(stream)
        logging.root.setLevel(logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(lvl)
    return logger

# EOF
