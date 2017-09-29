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

from analysis.batch import get_batch_system
import analysis.utils.config as _config
import analysis.utils.paths as _paths
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
        ALLOWED_CONFIG_DIFFS (list(str), optional):

    """

    VALIDATION = {}
    TOY_PATH_GETTER = None
    TOY_CONFIG_PATH_GETTER = None
    ALLOWED_CONFIG_DIFFS = []
    NTOYS_KEY = None
    NTOYS_PER_JOB_KEY = None

    def __init__(self, config_files, link_from, extend, overwrite):
        """Configure the toy submitter.

        Arguments:
            config_files (list[str]): Configuration files.
            link_from (str): Storage to link from.
            extend (bool): Extend the production?
            overwrite (bool): Overwrite an existing production?

        Raises:
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
            raise OSError("Cannot load configuration file: %s",
                          config_files)
        except KeyError as error:
            # logger.error(str(error))
            raise
        # Check conflicting arguments
        if extend and overwrite:
            logger.error("The --extend nor --overwrite options have been specified at the same time!")
            raise ValueError()
        # Store infotmation
        self.config = config
        # Assign link-from giving priority to the argument
        self.config['link-from'] = link_from if link_from else config.get('link-from', None)
        self.link_from = link_from
        self.extend = extend
        self.overwrite = overwrite
        # Get the batch system
        self.batch_system = get_batch_system()

    def run(self, script_to_run):
        """Run the script.

        If the output exists and no extension or overwrite has been configured, nothing
        is done.

        Arguments:
            script_to_run (str): Script to run in the cluster.

        Raises:
            AssertionError: If the qsub command cannot be found.
            AttributeError: If non-matching configuration file was found.
            OSError: If there is a problem preparing the output path.

        """
        config = dict(_config.unfold_config(self.config))
        # Check if it has not been produced yet
        # pylint: disable=E1102
        config_file_dest = self.TOY_CONFIG_PATH_GETTER(config['name'])
        # First check the config (we may have already checked)
        if os.path.exists(config_file_dest):  # It exists, check they match
            config_dest = _config.load_config(config_file_dest)
            if _config.compare_configs(config, config_dest).difference(set(self.ALLOWED_CONFIG_DIFFS)):
                logger.error("Non-matching configuration already exists with that name!")
                raise AttributeError()
        # Now check output
        _, expected_src, expected_dest = _paths.prepare_path(config['name'],
                                                             self.TOY_PATH_GETTER,
                                                             config['link-from'])
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
            raise OSError("Cannot find %s!" % script_to_run)
        script_args = []
        if config['link-from']:
            script_args.append('--link-from=%s' % config['link-from'])
        script_args.append(config_file_dest)
        # Prepare paths
        # pylint: disable=E1101
        _, log_file_fmt, _ = _paths.prepare_path(config['name'],
                                                 _paths.get_log_path,
                                                 None)  # No linking is done for logs
        # Calculate number of jobs and submit
        ntoys = config[self.NTOYS_KEY]
        ntoys_per_job = config.get(self.NTOYS_PER_JOB_KEY, ntoys)
        n_jobs = int(1.0*ntoys/ntoys_per_job)
        if ntoys % ntoys_per_job:
            n_jobs += 1
        # Submit!
        _config.write_config(self.config, config_file_dest)
        for _ in range(n_jobs):
            # Write the config file
            job_id = self.batch_system.submit_script(config['name'],
                                                     script_to_run,
                                                     script_args,
                                                     log_file_fmt,
                                                     **config.get('batch', {}))
            logger.info('Submitted JobID: %s', job_id)


# EOF
