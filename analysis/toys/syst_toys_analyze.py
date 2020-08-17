#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   syst_toys_analyze.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   22.01.2018
# =============================================================================
"""Analyze toys produced by `syst_toys.py`.

To configure, there are two mandatory configuration keys:
    + `toys-to-analyze` specifies the input toys (the `hdf` file is found via
        the `get_toy_fit_path` function).
    + `analysis` is a list of analysis tasks to perform. Each of these analysis
        tasks consists of a dictionary specifying an `action` and its relevant
        configuration.

"""

from __future__ import print_function

import argparse
import os

import pandas as pd

import analysis.utils.config as _config
import analysis.utils.paths as _paths
from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.toys.syst_analyze')


# Debug
def debug(toy_data, _):
    """Drop to an interactive debugging session.

    Arguments:
        toy_data (pd.HDFStore): Toy data to analyze

    Return:
        dict: Empty.

    """
    __import__('ipdb').set_trace()
    return dict()


# Count toys
def count_toys(toy_data, _):
    """Count number of toys.

    Arguments:
        toy_data (pd.HDFStore): Toy data to analyze

    Return:
        dict: number of toys in the 'ntoys' key.

    """
    logger.info("Executing 'count_toys' task")
    n_toys = toy_data['fit_results'].shape[0]
    print('Found {} toys'.format(n_toys))
    return {'ntoys': n_toys}


# Syst values
def get_central_intervals(toy_data, config):
    """Calculate central intervals for the given variables.

    Central intervals are given for 1, 2 and 3 sigma. Intervals are calculated
    as nominal - randomized, that means the result of fitting a randomized
    dataset with the nominal fit - fitting the same dataset with the randomized
    values as if they were nominal. The mean is also given as a measure of
    the bias.

    Arguments:
        toy_data (pd.HDFStore): Toy data to analyze
        config (dict): List of variables to study, given in the
            'variables' key.

    Return:
        list[dict]: Variable name, 1-, 2-, 3-sigma intervals and mean.

    Raises:
        KeyError: If the configuration doesn't contain the variables.
        ValueError: If any of the requested variables is not present in
            the toy data.

    """
    logger.info("Executing 'get_central_intervals' task")
    if 'variables' not in config or not isinstance(config['variables'], list):
        raise KeyError("Wrong central intervals configuration")
    var_list = config['variables']
    toy_results = toy_data['fit_results']
    central_intervals = []
    try:
        for variable in var_list:
            delta = toy_results["{}_nominal".format(variable)] - toy_results["{}_rand".format(variable)]
            percentiles = delta.quantile([0.0013, 0.02275, 0.15865, 0.84135, 0.97725, 0.9987]).values
            mean = delta.mean()
            central_intervals.append({'variable': variable,
                                      '1sigma': (percentiles[2], percentiles[3]),
                                      '2sigma': (percentiles[1], percentiles[4]),
                                      '3sigma': (percentiles[0], percentiles[5]),
                                      'mean': mean})
            print("Variable: {variable}\n  1sigma: {1sigma}\n  2sigma: {2sigma}\n  3sigma: {3sigma}\n  mean: {mean}"
                  .format(**central_intervals[-1]))
    except KeyError:
        logger.error("Missing variable in toys -> %s", variable)
        raise ValueError()
    return central_intervals


ANALYSIS_TASKS = {'debug': debug,
                  'count': count_toys,
                  'central-intervals': get_central_intervals}


def run(config_files):
    """Run the script.

    Analyze the toys according to the configuration.

    Arguments:
        config_files (list[str]): Path to the configuration files.

    Raise:
        OSError: If the configuration file or some other input does not exist.
        KeyError: If some configuration data are missing.
        RuntimeError: If there is a problem during the analysis.

    """
    try:
        config = _config.load_config(*config_files,
                                     validate=['toys-to-analyze',
                                               'analysis'])
    except OSError:
        raise OSError("Cannot load configuration files: {}".format(config_files))
    except _config.ConfigError as error:
        if 'toys-to-analyze' in error.missing_keys:
            logger.error("Toys to analyze not specified")
        if 'analysis' in error.missing_keys:
            logger.error("Analysis actions not specified")
        raise KeyError("ConfigError raised -> {}".format(error.missing_keys))
    except KeyError as error:
        logger.error("YAML parsing error -> %s", error)
        raise
    # Load the input toys
    input_toys = _paths.get_toy_fit_path(config['toys-to-analyze'])
    if not os.path.exists(input_toys):
        raise OSError("Cannot find input toy file: {}".format(input_toys))
    # Make sure analysis is in the correct format
    analysis_tasks = config['analysis']
    if not isinstance(analysis_tasks, list):
        analysis_tasks = [analysis_tasks]
    task_results = []
    with pd.HDFStore(input_toys) as hdf_file:
        for analysis_task in analysis_tasks:
            try:
                task_action = analysis_task.pop('action')
            except KeyError:
                logger.error("Missing analysis task action -> %s", analysis_task)
                raise KeyError("Malformed analysis task")
            if task_action not in ANALYSIS_TASKS:
                raise KeyError("Unknown analysis task -> {}".format(task_action))
            try:
                task_result = ANALYSIS_TASKS[task_action](hdf_file, analysis_task)
            except ValueError as error:
                raise RuntimeError(repr(error))
            if isinstance(task_result, dict):
                task_result = [task_result]
            if not isinstance(task_result, list):
                raise RuntimeError("Wrong format for task result -> {}".format(type(task_result)))
            task_results.extend(task_result)


def main():
    """Toy systematic analyzer application.

    Parses the command line and analyzes the toys, catching intermediate
    errors and transforming them to status codes.

    Status codes:
        0: All good.
        1: Error in the configuration files.
        2: Files missing (configuration or toys).
        3: Error analyzing toys.
        128: Uncaught error. An exception is logged.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Verbose output")
    parser.add_argument('config',
                        action='store', type=str, nargs='+',
                        help="Configuration files")
    args = parser.parse_args()
    if args.verbose:
        get_logger('analysis').setLevel(1)
        logger.setLevel(1)
    try:
        exit_status = 0
        run(args.config)
    except KeyError as error:
        exit_status = 1
        logger.exception("Bad configuration given -> %s", repr(error))
    except OSError as error:
        exit_status = 2
        logger.error(str(error))
    except RuntimeError as error:
        exit_status = 3
        logger.exception("Error analyzing toys")
    # pylint: disable=W0703
    except Exception as error:
        exit_status = 128
        logger.exception('Uncaught exception -> %s', repr(error))
    finally:
        parser.exit(exit_status)


if __name__ == "__main__":
    main()

# EOF
