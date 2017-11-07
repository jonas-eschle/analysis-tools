#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   syst_toys.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   24.10.2017
# =============================================================================
"""Toys for handling systematics.

These generate and fit in one go with some random variation of one or more parameters.

"""

import argparse
from collections import defaultdict
from timeit import default_timer

import pandas as pd
import numpy as np

import ROOT

from analysis.utils.logging_color import get_logger
from analysis.utils.monitoring import memory_usage
from analysis.data.hdf import modify_hdf
from analysis.physics import configure_model
from analysis.efficiency import get_acceptance
from analysis.fit import fit
from analysis.fit.result import FitResult
from analysis.batch import get_job_id
from analysis.toys.systematics import get_systematic
import analysis.utils.paths as _paths
import analysis.utils.config as _config
import analysis.utils.root as _root

logger = get_logger('analysis.toys.syst')


def run(config_files, link_from, verbose):
    """Run the script.

    Run a generate/fit sequence as many times as requested.

    Arguments:
        config_files (list[str]): Path to the configuration files.
        link_from (str): Path to link the results from.
        verbose (bool): Give verbose output?

    Raise:
        OSError: If the configuration file or some other input does not exist.
        AttributeError: If the input data are incompatible with a previous fit.
        KeyError: If some configuration data are missing.
        ValueError: If there is any problem in configuring the PDF factories.
        RuntimeError: If there is a problem during the fitting.

    """
    try:
        config = _config.load_config(*config_files,
                                     validate=['fit/nfits',
                                               'name',
                                               'data',
                                               'syst'])
    except OSError:
        raise OSError("Cannot load configuration files: {}".format(config_files))
    except _config.ConfigError as error:
        if 'fit/nfits' in error.missing_keys:
            logger.error("Number of fits not specified")
        if 'name' in error.missing_keys:
            logger.error("No name was specified in the config file!")
        if 'data' in error.missing_keys:
            logger.error("No input data specified in the config file!")
        if 'syst' in error.missing_keys:
            logger.error("No systematics configuration specified in config file!")
        raise KeyError("ConfigError raised -> {}".format(error.missing_keys))
    except KeyError as error:
        logger.error("YAML parsing error -> %s", error)
    model_name = config['fit'].get('model', 'model')  # TODO: 'model' returns name?
    try:
        model_config = config[model_name]
    except KeyError as error:
        logger.error("Missing model configuration -> %s", str(error))
        raise KeyError("Missing model configuration")
    # Load fit model
    try:
        fit_model = configure_model(model_config)
    except KeyError:
        logger.exception('Error loading model')
        raise ValueError('Error loading model')
    # Fit strategies
    fit_strategies = config['fit'].get('strategies', ['simple'])  # unused
    if not fit_strategies:
        logger.error("Empty fit strategies were specified in the config file!")
        raise KeyError()
    # Some info
    nfits = config['fit'].get('nfits-per-job', config['fit']['nfits'])
    logger.info("Doing %s generate/fit sequences", nfits)
    logger.info("Fit job name: %s", config['name'])
    if link_from:
        config['link-from'] = link_from
    if 'link-from' in config:
        logger.info("Linking toy data from %s", config['link-from'])
    else:
        logger.debug("No linking specified")
    # Now load the acceptance
    try:
        acceptance = get_acceptance(config['acceptance']) \
            if 'acceptance' in config \
            else None
    except _config.ConfigError as error:
        raise KeyError("Error loading acceptance -> {}".format(error))
    # Fit strategy
    fit_strategy = config['fit'].get('strategy', 'simple')
    # Load systematic configuration
    systematic = get_systematic(config['syst'])(model=fit_model, config=config['syst'])
    # Set seed
    job_id = get_job_id()
    if job_id:
        seed = int(job_id.split('.')[0])
    else:
        import random
        job_id = 'local'
        seed = random.randint(0, 100000)
    np.random.seed(seed=seed)
    ROOT.RooRandom.randomGenerator().SetSeed(seed)
    # Start looping
    fit_results = defaultdict(list)
    logger.info("Starting sampling-fit loop (print frequency is 20)")
    initial_mem = memory_usage()
    initial_time = default_timer()
    for fit_num in range(nfits):
        # Logging
        if (fit_num+1) % 20 == 0:
            logger.info("  Fitting event %s/%s", fit_num+1, nfits)
        # Generate a dataset
        try:
            dataset = systematic.get_dataset(acceptance)
            fit_result = fit(fit_model,
                             model_name,
                             fit_strategy,
                             dataset,
                             verbose,
                             Extended=config['fit'].get('extended', False),
                             Minos=config['fit'].get('minos', False))
        except ValueError:
            raise RuntimeError()
        except Exception:
            logger.exception()
            raise RuntimeError()  # TODO: provide more information?
        # Now results are in fit_parameters
        result = FitResult().from_roofit(fit_result).to_plain_dict()
        result['fitnum'] = fit_num
        fit_results[fit_num].append(result)
        _root.destruct_object(fit_result)
        _root.destruct_object(dataset)
        logger.debug("Cleaning up")
    logger.info("Fitting loop over")
    logger.info("--> Memory leakage: %.2f MB/sample-fit", (memory_usage() - initial_mem)/nfits)
    logger.info("--> Spent %.0f ms/sample-fit", (default_timer() - initial_time)*1000.0/nfits)
    logger.info("Saving to disk")
    data_frame = pd.DataFrame(fit_results)
    fit_result_frame = pd.concat([data_frame,
                                  pd.concat([pd.DataFrame({'seed': [seed],
                                                           'jobid': [job_id]})]
                                            * data_frame.shape[0]).reset_index(drop=True)],
                                 axis=1)
    try:
        # pylint: disable=E1101
        with _paths.work_on_file(config['name'],
                                 path_func=_paths.get_toy_fit_path,
                                 link_from=config.get('link-from', None)) as toy_fit_file:
            with modify_hdf(toy_fit_file) as hdf_file:
                # First fit results
                hdf_file.append('fit_results', fit_result_frame)
                # Generator info
                hdf_file.append('input_values', pd.DataFrame([systematic.get_input_values()]))
            logger.info("Written output to %s", toy_fit_file)
            if 'link-from' in config:
                logger.info("Linked to %s", config['link-from'])
    except OSError as excp:
        logger.error(str(excp))
        raise
    except ValueError as error:
        logger.exception("Exception on dataset saving")
        raise RuntimeError(str(error))


def main():
    """Toy systematic fitting application.

    Parses the command line and fits the toys, catching intermediate
    errors and transforming them to status codes.

    Status codes:
        0: All good.
        1: Error in the configuration files.
        2: Files missing (configuration or toys).
        3: Error configuring physics factories.
        4: Error in the event generation. An exception is logged.
        5: Input data is inconsistent with previous fits.
        128: Uncaught error. An exception is logged.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Verbose output")
    parser.add_argument('--link-from',
                        action='store', type=str, default='',
                        help="Folder to actually store the fit results")
    parser.add_argument('config',
                        action='store', type=str, nargs='+',
                        help="Configuration files")
    args = parser.parse_args()
    if args.verbose:
        get_logger('analysis').setLevel(1)
        logger.setLevel(1)
    else:
        ROOT.RooMsgService.instance().setGlobalKillBelow(ROOT.RooFit.WARNING)
    try:
        exit_status = 0
        run(args.config, args.link_from, args.verbose)
    except KeyError:
        exit_status = 1
        logger.exception("Bad configuration given")
    except OSError as error:
        exit_status = 2
        logger.error(str(error))
    except ValueError:
        exit_status = 3
        logger.exception("Problem configuring physics factories")
    except RuntimeError as error:
        exit_status = 4
        logger.error("Error in fitting events")
    except AttributeError as error:
        exit_status = 5
        logger.error("Inconsistent input data -> %s", error)
    # pylint: disable=W0703
    except Exception as error:
        exit_status = 128
        logger.exception('Uncaught exception -> %s', repr(error))
    finally:
        parser.exit(exit_status)


if __name__ == "__main__":
    main()

# EOF
