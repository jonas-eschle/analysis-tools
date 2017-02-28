#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   submit_fit_toys.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   14.02.2017
# =============================================================================
"""Submission of `fit_toys.py` to the cluster.

This submission is forced to happen through a config file in YAML format
to ensure reproducibility.

Mandatory configuration keys are:
    - name: Name of the job
    - fit/nfits: Total number of fits to perform.
    - fit/nfits-per-job: Number of fits produced per job.

Optional configuration keys:
    - batch/runtime: In the HH:MM:SS format. Defaults to 08:00:00.

"""

import argparse
import os

from analysis import get_global_var
import analysis.utils.paths as _paths
from analysis.utils.logging_color import get_logger
from analysis.utils.batch import ToySubmitter


logger = get_logger('analysis.toys.submit_generate')


# pylint: disable=too-few-public-methods
class FitSubmitter(ToySubmitter):
    """Specialization of ToySubmitter to submit the fitting of toys."""

    VALIDATION = {'name': "No name was specified in the config file!",
                  'fit/nfits': "Number of fits not specified!",
                  'fit/nfits-per-job': "Number of fits per job not specified!",
                  'model': "No pdfs were specified in the config file!",
                  'data': "No input data was specified in the config file!"}
    TOY_PATH_GETTER = _paths.get_toy_fit_path
    TOY_CONFIG_PATH_GETTER = _paths.get_toy_fit_config_path
    ALLOWED_CONFIG_DIFFS = ['gen/nevents',
                            'gen/nevents-per-job',
                            'batch/runtime']
    NTOYS_KEY = 'fit/nfits'
    NTOYS_PER_JOB_KEY = 'fit/nfits-per-job'


def main():
    """Toy fitting submission application.

    Parses the command line, configures the toy fitters and submit the
    jobs, catching intermediate errors and transforming them to status codes.

    Status codes:
        0: All good.
        1: Error in the configuration files.
        2: Error in preparing the output folders.
        3: Conflicting options given.
        4: A non-matching configuration file was found in the output.
        128: Uncaught error. An exception is logged.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--link-from',
                        action='store', type=str,
                        help="Folder to actually store the toy files")
    parser.add_argument('--extend',
                        action='store_true', default=False,
                        help="Extend previous production")
    parser.add_argument('--overwrite',
                        action='store_true', default=False,
                        help="Overwrite previous production")
    parser.add_argument('config',
                        action='store', type=str, nargs='+',
                        help="Configuration file")
    args = parser.parse_args()
    try:
        script_to_run = os.path.join(get_global_var('BASE_PATH'),
                                     'toys',
                                     'fit_toys.py')
        FitSubmitter(args.config,
                     args.link_from,
                     args.extend,
                     args.overwrite).run(script_to_run)
        exit_status = 0
    except KeyError:
        logger.error("Bad configuration given")
        exit_status = 1
    except OSError, error:
        logger.error(str(error))
        exit_status = 2
    except ValueError:
        logger.error("Conflicting options found")
        exit_status = 3
    except AttributeError:
        logger.error("Mismatching configuration found")
        exit_status = 4
    # pylint: disable=W0703
    except Exception as error:
        exit_status = 128
        logger.exception('Uncaught exception -> %s', repr(error))
    finally:
        parser.exit(exit_status)


if __name__ == "__main__":
    main()

# EOF
