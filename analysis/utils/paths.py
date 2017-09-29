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
from __future__ import print_function, division, absolute_import

import os
import inspect
from functools import partial

from contextlib import contextmanager

import fasteners

from analysis import get_global_var
from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.utils.paths')


def _get_path(dirs, extension, name_transformation, name, *args, **kwargs):
    """Get the path for an object.

    The path is $BASE_PATH/{'/'.join(dirs)}/{name_transformation(name, args, kwargs)}{extension}.

    Arguments:
        dirs (list): Parent directories of the object path.
        extension (str): Extension of the file (including the dot).
        name_transformation (Callable, optional): Function to transform the name of the path.
        name (str): Name of the object.
        *args (list): Positional arguments to be passed to `name_transformation`.
        *kwargs (list): Keyword arguments to be passed to `name_transformation`.

    Returns:
        str: Absolute path of the object.

    """
    assert extension.startswith('.'), "Extension is expected to start with '.'. " \
                                      "Given extension: {}".format(extension)

    path = os.path.join(*([get_global_var('BASE_PATH')] +
                          dirs + [name_transformation(name, args, kwargs)]))
    if not path.endswith(extension):
        path += extension

    return path


def register_path(path_type,
                  parent_dirs,
                  extension,
                  name_transformation=lambda name, args, kwargs: name):
    """Register path function.

    This will create a function in the module namespace called `get_{path_type}_path`.

    Arguments:
        path_type (str): Type of path to register. Defines the name of the registered function.
        parent_dirs (list): List of parent dirs (on top of BASE_PATH) of the path we want to register.
        extension (str): Extension of the file, including the dot.
        name_transformation (Callable, optional): Function to transform the name of the path
            when calling the `get_{path_type}_path`. It needs to have three arguments: `name`,
            `args` and `kwargs`, which are passed when executing the `get_{path_type}_path` function.
            Defaults to the identity:

                ```
                lambda name, args, kwargs: name
                ```

    Returns:
        Callable: The created function.

    Raises:
        ValueError: If the signature of the `name_transformation` doesn't match the specifications.
        KeyError: If the path has already been registered.

    """
    # Checks
    if not extension.startswith('.'):
        extension = '.' + extension
    try:  # PY3
        name_transformation_args = inspect.getfullargspec(name_transformation).args
    except AttributeError:  # PY2
        name_transformation_args = inspect.getargspec(name_transformation).args
    if len(name_transformation_args) != 3:
        raise ValueError("The name transformation function needs to have 3 arguments")
    # Register the partialled function in globals
    func_name = 'get_' + path_type + '_path'
    if func_name in globals():
        raise KeyError("Path type already registered -> %s" % path_type)
    logger.debug("Registering path %s", func_name)
    func = partial(_get_path, parent_dirs, extension, name_transformation)
    # Create the docstring
    func.__doc__ = """Get the path for %s.

    The file name is {BASE_PATH}/%s/{name}%s and its existence is
    not checked.

    Arguments:
        name (str): Name of the object.

    Returns:
        str: Absolute path of the file.

    """ % (path_type, os.sep.join(parent_dirs), extension)
    globals()['get_' + path_type + '_path'] = func
    return func


# Register path functions
get_toy_path = register_path('toy', ['data_files', 'toys', 'gen'], 'hdf')
get_toy_config_path = register_path('toy_config', ['data_files', 'toys', 'gen'], 'yaml')
get_toy_fit_path = register_path('toy_fit', ['data_files', 'toys', 'fit'], 'hdf')
get_toy_fit_config_path = register_path('toy_fit_config', ['data_files', 'toys', 'fit'], 'yaml')
get_log_path = register_path('log', ['data_files', 'logs'], 'log')
get_efficiency_path = register_path('efficiency', ['data_files', 'efficiency'], 'yaml')
get_acceptance_path = register_path('acceptance', ['data_files', 'acceptance'], 'yaml')
get_genlevel_mc_path = register_path('genlevel_mc', ['data_files', 'mc'], 'xgen',
                                     lambda name, args, kwargs: os.path.join(str(kwargs['evt_type']),
                                                                             name))
get_genlevel_histos_path = register_path('genlevel_histos', ['data_files', 'mc'], 'root',
                                         lambda name, args, kwargs: os.path.join(str(kwargs['evt_type']),
                                                                                 name + '_histos'))
get_plot_style_path = register_path('plot_style', ['data_files', 'styles'], 'mplstyle',
                                    lambda name, args, kwargs: 'matplotlib_' + name)
get_fit_result_path = register_path('fit_result', ['data_files', 'fit'], 'yaml')


def prepare_path(name, path_func, link_from, *args, **kwargs):
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
        *args (list): Extra arguments for the `path_func`.
        **kwargs (dict): Extra arguments for the `path_func`.

    Returns:
        tuple (bool, str, str): Need to do soft-linking, path of true output file,
            path of soft-link output.

    """
    do_link = False
    dest_base_dir = get_global_var('BASE_PATH')
    src_base_dir = link_from or dest_base_dir
    if dest_base_dir != src_base_dir:
        do_link = True
        if not os.path.exists(src_base_dir):
            raise OSError("Cannot find storage folder -> %s" % src_base_dir)
    dest_file_name = path_func(name, *args, **kwargs)
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
