#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   paths.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.01.2017
# =============================================================================
"""Manage paths.

The structure is fixed:
    - Toys:
        * Generated data are stored in `analysis/data/toys/gen`.
        * Toy results are stored in `analysis/data/toys/results`.
    - Logs are in `analysis/data/logs`.

These may just be soft links, depending on how they have been run.

"""

import os

from contextlib import contextmanager

import fasteners

import analysis
from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.utils.paths')


def get_toy_path(name):
    """Get the name of the toy MC generated file.

    The file name is {BASE_PATH}/data/toys/gen/{name}.hdf and its existence is
    not checked.

    Arguments:
        name (str): Name of the MC generation.

    Returns:
        str: Absolute path of the toys file.

    """
    return os.path.join(analysis.get_global_var('BASE_PATH'),
                        'data', 'toys', 'gen', name + '.hdf')


def get_toy_config_path(name):
    """Get the name of the config file for the toy generation.

    The file name is {BASE_PATH}/data/toys/gen/{name}.yaml and its existence is
    not checked.

    Arguments:
        name (str): Name of the MC generation.

    Returns:
        str: Absolute path of the config file.

    """
    return os.path.join(analysis.get_global_var('BASE_PATH'),
                        'data', 'toys', 'gen', name + '.yaml')


def get_toy_fit_path(name):
    """Get the name of the fit results for toys.

    The file name is {BASE_PATH}/data/toys/fit/{name}.hdf and its existence is
    not checked.

    Arguments:
        name (str): Name of the fit file.

    Returns:
        str: Absolute path of the toys file.

    """
    return os.path.join(analysis.get_global_var('BASE_PATH'),
                        'data', 'toys', 'fit', name + '.hdf')


def get_toy_fit_config_path(name):
    """Get the name of the config file for the toy fits.

    The file name is {BASE_PATH}/data/toys/fit/{name}.yaml and its existence is
    not checked.

    Arguments:
        name (str): Name of the toy fit generation.

    Returns:
        str: Absolute path of the config file.

    """
    return os.path.join(analysis.get_global_var('BASE_PATH'),
                        'data', 'toys', 'fit', name + '.yaml')


def get_log_path(name, is_batch=True):
    """Get the path for log files.

    The file name is {BASE_PATH}/data/logs/{name}_PBSJOBID.log and its existence is
    not checked.

    Arguments:
        name (str): Name of the job.
        is_batch (bool, optional): Is this a log file for a batch job?

    Returns:
        str: Absolute path of the log fil.

    """
    jobid = '_${PBS_JOBID}' if is_batch else ''
    return os.path.join(analysis.get_global_var('BASE_PATH'),
                        'data', 'logs', name + jobid + '.log')


def get_efficiency_path(name):
    """Get the name of the config files for the efficiency descriptions.

    The file name is {BASE_PATH}/data/efficiency/{name}.yaml and its existence is
    not checked.

    Arguments:
        name (str): Name of the efficiency.

    Returns:
        str: Absolute path of the config file.

    """
    return os.path.join(analysis.get_global_var('BASE_PATH'),
                        'data', 'efficiency', name + '.yaml')


def prepare_path(name, path_func, link_from):
    """Build the folder structure for any output.

    The output file name is obtained from `path_func` and the possibility of
    having soft links is taken into account through the `link_from` argument.

    It takes the output file_name and builds all the folder structure from
    `BASE_PATH` until that file. If soft links have to be taken into account,
    the same relative path is built from the `link_from` folder.

    Arguments:
        name (str): Name of the job. To be passed to `path_func`.
        path_func (Callable): Function to execute to get the path.
        link_from (str): Base directory for symlinking. If `None`, no symlinking
            is done.

    Returns:
        tuple (bool, str, str): Need to do soft-linking, path of true output file,
            path of soft-link output.

    """
    do_link = False
    dest_base_dir = analysis.get_global_var('BASE_PATH')
    src_base_dir = link_from or dest_base_dir
    if dest_base_dir != src_base_dir:
        do_link = True
        if not os.path.exists(src_base_dir):
            raise OSError("Cannot find storage folder -> %s" % src_base_dir)
    dest_file_name = path_func(name)
    rel_file_name = os.path.relpath(dest_file_name,
                                    dest_base_dir)
    src_file_name = os.path.join(src_base_dir, rel_file_name)
    # Create dirs
    rel_dir = os.path.dirname(rel_file_name)
    for dir_ in (dest_base_dir, src_base_dir):
        if not os.path.exists(os.path.join(dir_, rel_dir)):
            os.makedirs(os.path.join(dir_, rel_dir))
    return do_link, src_file_name, dest_file_name


@contextmanager
def work_on_file(name, path_func, link_from=None):
    """Context manager for working on a file.

    The path is prepared (@see `prepare_path`), taking into account possible links,
    and the context manager returns. On exit, the symlinking (if needed) is done.
    Additionally, it locks the file during the whole process.

    Arguments:
        name (str): Name of the file. To be passed to `path_func`.
        path_func (Callable): Function to execute to get the path.
        link_from (str, optional): Base directory for symlinking. The default is `None`,
            in which case no symlinking is done.

    Yields:
        str: Path ot the file.

    Raises:
        OSError: If there is a problem preparing the path.

    """
    def link_files(*files):
        """Perform simlinking of files.

        Note:
            If the destination file exists and it's not a link, it is
            removed.

        Arguments:
            *files (list[tuple]): Pairs of (source, destination) names
                for symlinking.

        """
        for src_file, dest_file in files:
            if not os.path.exists(src_file):
                continue
            if os.path.exists(dest_file):
                if not os.path.islink(dest_file):
                    os.remove(dest_file)
            if not os.path.exists(dest_file):
                os.symlink(src_file, dest_file)

    try:
        do_link, src_file, dest_file = prepare_path(name, link_from, path_func)
    except OSError as error:
        raise OSError("Error preparing path -> %s" % str(error))
    lock_file = os.path.join(os.path.dirname(src_file),
                             '.%s.lock' % os.path.split(src_file)[1])
    with fasteners.InterProcessLock(lock_file):
        logger.debug("Got lock!")
        yield src_file
        if do_link:
            link_files((src_file, dest_file))
        logger.debug('Releasing lock!')

# EOF
