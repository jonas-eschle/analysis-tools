#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   submitter.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   31.05.2017
# =============================================================================
"""Toy submitter base class."""
from __future__ import print_function, division, absolute_import

import os

import analysis.utils.config as _config
import analysis.utils.paths as _paths
from analysis.batch import get_batch_system
from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.toys.submitter')


# pylint: disable=too-few-public-methods
class ToySubmitter(object):
    """Manage toy job submission.

    This class must be inherited and the mandatory attributes need to be defined.

    Attributes:
        TOY_PATH_GETTER` (Callable): Function to get the output path of the toy.
        TOY_CONFIG_PATH_GETTER (Callable): Function to get the output path of the
            toy configuration.
        NTOYS_KEY (str): Key in the configuration that can be used to extract the
            total number of toys to run.
        NTOYS_PER_JOB_KEY (str): Key in the configuration that can be used to extract
            the number of toys per job.
        VALIDATION (dict, optional): Pairs of key, message to validate the input
            configuration. If the key is not present, KeyError is raised and the
            message logged.
        ALLOWED_CONFIG_DIFFS (list(str), optional): Allowed differences between new and
            stored configurations.

    """

    VALIDATION = {}
    TOY_PATH_GETTER = None
    TOY_CONFIG_PATH_GETTER = None
    ALLOWED_CONFIG_DIFFS = []
    NTOYS_KEY = None
    NTOYS_PER_JOB_KEY = None

    def __init__(self, config_files, link_from, extend, overwrite, verbose=False):
        """Configure the toy submitter.

        Arguments:
            config_files (list[str]): Configuration files.
            link_from (str): Storage to link from.
            extend (bool): Extend the production?
            overwrite (bool): Overwrite an existing production?

        Raise:
            NotImplementedError: If some of the mandatory attributes are not
                set.
            OSError: If there is a problem with the configuration file, either in
                loading or validation.
            ValueError: If conflicting options are passed.

        """
        # Check the getters
        if any(getter is None
               for getter in (self.TOY_PATH_GETTER,
                              self.TOY_CONFIG_PATH_GETTER,
                              self.NTOYS_KEY,
                              self.NTOYS_PER_JOB_KEY)):
            raise NotImplementedError("Getters not implemented")
        try:
            config = _config.load_config(*config_files,
                                         validate=self.VALIDATION.keys())
        except _config.ConfigError as error:
            for key, error_message in self.VALIDATION.items():
                if key in error.missing_keys:
                    logger.error(error_message)
            raise KeyError()
        except OSError as error:
            raise OSError("Cannot load configuration file: {}"
                          .format(config_files))
        except KeyError as error:
            # logger.error(str(error))
            raise
        # Check conflicting arguments
        if extend and overwrite:
            logger.error("The --extend nor --overwrite options have been specified at the same time!")
            raise ValueError()
        # Store infotmation
        self.config = config
        self.allowed_config_diffs = set([self.NTOYS_KEY, self.NTOYS_PER_JOB_KEY, 'batch/runtime']
                                        + self.ALLOWED_CONFIG_DIFFS)
        # Assign link-from giving priority to the argument
        self.config['link-from'] = link_from if link_from else config.get('link-from')
        self.link_from = link_from
        self.extend = extend
        self.overwrite = overwrite
        self.verbose = verbose
        # Get the batch system
        self.batch_system = get_batch_system()

    def run(self, script_to_run):
        """Run the script.

        If the output exists and no extension or overwrite has been configured, nothing
        is done.

        Arguments:
            script_to_run (str): Script to run in the cluster.

        Raise:
            AssertionError: If the qsub command cannot be found.
            AttributeError: If non-matching configuration file was found.
            OSError: If there is a problem preparing the output path.

        """
        flat_config = dict(_config.unfold_config(self.config))
        # Check if it has not been produced yet
        # pylint: disable=E1102
        config_file_dest = self.TOY_CONFIG_PATH_GETTER(self.config['name'])
        # First check the config (we may have already checked)
        if os.path.exists(config_file_dest):  # It exists, check they match
            config_dest = _config.load_config(config_file_dest)
            if _config.compare_configs(flat_config, config_dest).difference(self.allowed_config_diffs):
                logger.error("Non-matching configuration already exists with that name!")
                raise AttributeError()
        # Now check output
        _, expected_src, expected_dest = _paths.prepare_path(name=self.config['name'],
                                                             path_func=self.TOY_PATH_GETTER,
                                                             link_from=self.config['link-from'])
        # Check file existence
        if os.path.exists(expected_src):
            logger.warning("Output data file exists! %s", expected_src)
            if self.overwrite:
                os.remove(expected_src)
                if os.path.exists(expected_dest):
                    os.remove(expected_dest)
            else:
                # Create de symlink if necessary
                if not os.path.exists(expected_dest):
                    os.symlink(expected_src, expected_dest)
                if not self.extend:
                    logger.info("Nor --extend nor --overwrite have been specified. Nothing to do.")
                    return
        # Source doesn't exist, delete the destination if needed
        else:
            if os.path.exists(expected_dest):
                os.remove(expected_dest)
        # Some bookkeeping
        if not os.path.exists(script_to_run):
            raise OSError("Cannot find {}!".format(script_to_run))
        script_args = []
        if self.config['link-from']:
            script_args.append('--link-from={}'.format(self.config['link-from']))
        if self.verbose:
            script_args.append('--verbose')
        script_args.append(config_file_dest)
        # Prepare paths
        # pylint: disable=E1101
        _, log_file_fmt, _ = _paths.prepare_path(name=self.config['name'],
                                                 path_func=_paths.get_log_path,
                                                 link_from=None)  # No linking is done for logs
        # Calculate number of jobs and submit
        ntoys = flat_config[self.NTOYS_KEY]
        ntoys_per_job = flat_config.get(self.NTOYS_PER_JOB_KEY, ntoys)
        n_jobs = int(1.0 * ntoys / ntoys_per_job)
        if ntoys % ntoys_per_job:
            n_jobs += 1
        # Submit!
        _config.write_config(self.config, config_file_dest)
        for _ in range(n_jobs):
            # Write the config file
            job_id = self.batch_system.submit_script(job_name=self.config['name'],
                                                     cmd_script=script_to_run,
                                                     script_args=script_args,
                                                     log_file=log_file_fmt,
                                                     **self.config.get('batch', {}))
            logger.info('Submitted JobID: %s', job_id)

# EOF
