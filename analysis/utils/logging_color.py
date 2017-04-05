#!/usr/bin/env python
# =============================================================================
# @file   logging_color.py
# @author C. Marin Benito (carla.marin.benito@cern.ch)
# @date   16.03.2016
# =============================================================================
"""
This functions configures a logger using logging and colorlog
and returns the logger for further usage
By default, time, name of the logger and message with the default
colorlog color scheme are printed.
The threshold level for displaying messages and the format of the
logger can be configured with the lvl and format arguments
"""

import logging
import colorlog


def get_logger(name, lvl=logging.INFO, format_=None):
    """Configure logging.

    Arguments:
        name (str): Name of the logger.
        lvl (int, optional): Logging level. Defaults to
            `logging.INFO`.
        format_ (str): Logger formatting string

    Returns:
        `logging.Logger`: The requested logger.

    """
    if not format_:
        format_ = ("%(asctime)s - %(name)s | "
                   "%(log_color)s%(levelname)-8s%(reset)s | "
                   "%(log_color)s%(message)s%(reset)s")
    if not logging.getLogger().isEnabledFor(lvl):
        logging.root.setLevel(lvl)
    logger = logging.getLogger(name)
    if not len(logger.handlers):
        formatter = colorlog.ColoredFormatter(format_)
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        logger.setLevel(lvl)
        logger.addHandler(stream)
    return logger

# EOF
