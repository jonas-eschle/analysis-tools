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

import analysis


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

    The file name is {BASE_PATH}/data/toys/gen/{name}.yml and its existence is
    not checked.

    Arguments:
        name (str): Name of the MC generation.

    Returns:
        str: Absolute path of the config file.

    """
    return os.path.join(analysis.get_global_var('BASE_PATH'),
                        'data', 'toys', 'gen', name + '.yml')


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

    The file name is {BASE_PATH}/data/toys/fit/{name}.yml and its existence is
    not checked.

    Arguments:
        name (str): Name of the toy fit generation.

    Returns:
        str: Absolute path of the config file.

    """
    return os.path.join(analysis.get_global_var('BASE_PATH'),
                        'data', 'toys', 'fit', name + '.yml')


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


def prepare_path(name, link_from, path_func):
    """Build the folder structure for any output.

    The output file name is obtained from `path_func` and the possibility of
    having soft links is taken into account through the `link_from` argument.

    It takes the output file_name and builds all the folder structure from
    `BASE_PATH` until that file. If soft links have to be taken into account,
    the same relative path is built from the `link_from` folder.

    Arguments:
        name (str): Name of the job. To be passed to `path_func`.
        link_from (str): Base directory for symlinking. If `None`, no symlinking
            is done.
        path_func (Callable): Function to execute to get the path.

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


# EOF
