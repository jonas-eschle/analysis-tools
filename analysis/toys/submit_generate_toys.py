#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   submit_generate_toys.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   17.01.2017
# =============================================================================
"""Submission of `generate_toys.py` to the cluster.

This submission is forced to happen through a config file in YAML format
to ensure reproducibility.

Mandatory configuration keys are:
    - name: Name of the job
    - gen/nevents: Total number of events to produce.
    - gen/nevents-per-job: Number of events produced per job.

Optional configuration keys:
    - batch/runtime: In the HH:MM:SS format. Defaults to 08:00:00.

"""

import argparse
import os

from analysis import get_global_var
from analysis.utils.logging_color import get_logger
import analysis.utils.paths as _paths
from analysis.utils.batch import ToySubmitter


logger = get_logger('analysis.toys.submit_generate')


# pylint: disable=too-few-public-methods
class GenerationSubmitter(ToySubmitter):
    """Specialization of ToySubmitter to submit generation of toys."""

    VALIDATION = {'name': "No name was specified in the config file!",
                  'gen/nevents': "Number of events not specified!",
                  'gen/nevents-per-job': "Number of events per job not specified!",
                  'pdfs': "No pdfs were specified in the config file!"}
    TOY_PATH_GETTER = _paths.get_toy_path
    TOY_CONFIG_PATH_GETTER = _paths.get_toy_config_path
    ALLOWED_CONFIG_DIFFS = ['gen/nevents',
                            'gen/nevents-per-job',
                            'batch/runtime']
    NTOYS_KEY = 'gen/nevents'
    NTOYS_PER_JOB_KEY = 'gen/nevents-per-job'


def main(script_to_run):
    """Toy generation submission application.

    Parses the command line, configures the toy fitters and submit the
    jobs, catching intermediate errors and transforming them to status codes.

    Status codes:
        0: All good.
        1: Error in the configuration files.
        2: Error in preparing the output folders.
        3: Conflicting options given.
        4: A non-matching configuration file was found in the output.
        128: Uncaught error. An exception is logged.

    Arguments:
        script_to_run (str): Script to submit.

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
                                     'submit_toys.py')
        GenerationSubmitter(args.config,
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
    main(__file__.replace('submit_', ''))

# EOF
