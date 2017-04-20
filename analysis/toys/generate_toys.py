#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   generate_toys.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   11.01.2017
# =============================================================================
"""Toy generation."""

import argparse
import os

import pandas as pd
import ROOT

from analysis.physics import configure_model
from analysis.utils.root import destruct_object
from analysis.utils.config import load_config, ConfigError
from analysis.utils.logging_color import get_logger
# pylint: disable=E0611
from analysis.utils.paths import get_toy_path, work_on_file
from analysis.data.converters import pandas_from_dataset
from analysis.data.hdf import modify_hdf


logger = get_logger('analysis.toys.generate')


def generate(physics_factory, configuration):
    """Perform generation of toys.

    Arguments:
        physics_factory (`analysis.physics.PhysicsFactory`): Physics factory object to get
            observables, parameters and PDFs from.
        configuration (dict): Configuration.

    Returns:
        `pandas.DataFrame`: Generated events.

    """
    def generate_events(gen_pdf, obs_set, n_events):
        """Generate events according to the given PDF.

        Result is converted to a pandas data frame.

        Arguments:
            gen_pdf (`ROOT.RooAbsPdf`): PDF to use for generation.
            obs_set (`ROOT.RooArgSet`): Observables to generate.
            n_events (int): Number of events to generate.

        Returns:
            `pandas.DataFrame`: Generated events.

        """
        data = gen_pdf.generate(obs_set, n_events)
        dataframe = pandas_from_dataset(data)
        destruct_object(data)
        return dataframe

    # pylint: disable=C0103
    observables = physics_factory.get_observables()
    obs_set = ROOT.RooArgSet()
    for obs in observables:
        obs_set.add(obs)
    fit_params = physics_factory.get_fit_parameters()
    return generate_events(physics_factory.get_pdf()("GenPdf", "GenPdf",
                                                     *(observables + fit_params)),
                           obs_set,
                           configuration['gen']['nevents'])


def run(config_files, link_from):
    """Run the script.

    Arguments:
        config_files (list[str]): Path to the configuration files.
        link_from (str): Path to link the results from.

    Raises:
        KeyError: If some configuration data are missing.
        OSError: If there either the configuration file does not exist or if
            there is a problem preparing the output path.
        ValueError: If there is any problem in configuring the PDF factories.
        RuntimeError: If there is a problem during the generation.

    """
    # Configure
    try:
        config = load_config(*config_files,
                             validate=['gen/nevents',
                                       'name',
                                       'gen-model'])
    except OSError:
        raise OSError("Cannot load configuration files: %s",
                      config_files)
    except ConfigError as error:
        if 'gen/nevents' in error.missing_keys:
            logger.error("Number of events not specified")
        if 'name' in error.missing_keys:
            logger.error("No name was specified in the config file!")
        if 'gen-model' in error.missing_keys:
            logger.error("No generation model were specified in the config file!")
        raise KeyError("ConfigError raised -> %s" % error.missing_keys)
    except KeyError as error:
        logger.error("YAML parsing error -> %s", error)
        raise
    # Ignore renaming
    logger.info("Generating %s events", config['gen']['nevents'])
    logger.info("Generation job name: %s", config['name'])
    if link_from:
        config['link-from'] = link_from
    if 'link-from' in config:
        logger.info("Linking toy data from %s", config['link-from'])
    else:
        logger.debug("No linking specified")
    # Set seed
    try:
        job_id = os.environ['PBS_JOBID']
        seed = int(job_id.split('.')[0])
    except KeyError:
        import random
        job_id = 'local'
        seed = random.randint(0, 100000)
    ROOT.RooRandom.randomGenerator().SetSeed(seed)
    # Generate
    try:
        physics = configure_model(config['gen-model'])
    except KeyError as error:
        logger.error("Cannot find physics factory")
        raise ValueError('%s' % error)
    except ValueError:
        logger.error("Problem dealing with shared parameters")
        raise
    try:
        dataset = generate(physics, config)
    except ValueError as error:
        logger.exception("Exception on generation")
        raise RuntimeError(str(error))
    # Get toy information
    toy_info = {var.GetName(): [var.getVal()]
                for var
                in physics.get_gen_parameters()}
    toy_info.update({'seed': [seed],
                     'jobid': [job_id],
                     'nevents': [config['gen']['nevents']]})
    try:
        # Save
        with work_on_file(config['name'],
                          config.get('link-from', None),
                          get_toy_path) as toy_file:
            with modify_hdf(toy_file) as hdf_file:
                hdf_file.append('data', dataset.assign(jobid=job_id))
                hdf_file.append('toy_info', pd.DataFrame(toy_info))
        # Say something
        logger.info("Written output to %s", toy_file)
        if 'link-from' in config:
            logger.info("Linked to %s", config['link-from'])
    except OSError, excp:
        logger.error(str(excp))
        raise
    except ValueError as error:
        logger.exception("Exception on dataset saving")
        raise RuntimeError(str(error))


def main():
    """Toy generation application.

    Parses the command line and runs the toys, catching intermediate
    errors and transforming them to status codes.

    Status codes:
        0: All good.
        1: Error in the configuration files.
        2: Files missing (configuration or toys).
        3: Error configuring physics factories.
        4: Error in the event generation.
        128: Uncaught error. An exception is logged.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--link-from',
                        action='store', type=str, default='',
                        help="Folder to actually store the toy files")
    parser.add_argument('config',
                        action='store', type=str, nargs='+',
                        help="Configuration files")
    args = parser.parse_args()
    try:
        run(args.config, args.link_from)
        exit_status = 0
    except KeyError:
        exit_status = 1
        logger.error("Bad configuration given")
    except OSError, error:
        exit_status = 2
        logger.error(str(error))
    except ValueError:
        exit_status = 3
        logger.error("Problem configuring physics factories")
    except RuntimeError as error:
        exit_status = 4
        logger.error("Error in generating events")
    # pylint: disable=W0703
    except Exception as error:
        exit_status = 128
        logger.exception('Uncaught exception -> %s', repr(error))
    finally:
        parser.exit(exit_status)


if __name__ == "__main__":
    main()

# EOF
