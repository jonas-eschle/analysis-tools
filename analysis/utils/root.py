#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   root.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.01.2017
# =============================================================================
"""Utilities for interacting with ROOT."""

import os
import subprocess

import ROOT


def load_library(name, lib_dirs=None, debug=False, force=False):
    """Load C++ ROOT libraries, compiling if necessary.

    Libraries are looked for first in the current folder or `lib_dir`.
    If an absolute path is specified, it takes priority.

    Arguments:
        name (str): Name of the library to load (.cxx not needed).
        lib_dirs (list, optional): Folders storing the library sources.
        debug (bool, optional): Compile the library en debug mode? Defaults
            to `False`.
            force (bool, optional): Force recompilation? Defaults to `False`.

    Returns:
        bool: Was the operation successful?

    """
    if name.endswith('+'):
        name = name.split('+')[0]
    lib_dirs = lib_dirs if lib_dirs else []
    # Determine file to load
    for extension in ('.cc', '.cxx'):
        if not os.path.splitext(name)[1]:
            file_name = name + extension
        if not os.path.isabs(file_name):
            if os.path.exists(os.path.abspath(file_name)):
                name = os.path.abspath(file_name)
            elif not os.path.isfile(file_name):
                new_name = file_name
                for lib_dir in lib_dirs:
                    new_name = os.path.join(lib_dir, file_name)
                    if os.path.isfile(new_name):
                        name = new_name
                        break
        if name == file_name:
            break
    if not os.path.exists(name):
        raise OSError("Cannot locate library")
    options = 'k'
    if force:
        options += "f"
    if debug:
        options += "g"
    try:
        # ROOT.gSystem.CompileMacro(name, options)
        command = 'root -l -q -b -e gSystem->CompileMacro(\"%s\",\"%s\")' % (name, options)
        subprocess.check_output(command.split())
        # If it returns 0 means the compilation failed (thanks ROOT)
        return False
    except subprocess.CalledProcessError:  # This is what we expect
        ROOT.gSystem.Load(name.replace('.c', '_c'))
        return True
    #  ROOT.gInterpreter.ProcessLine(".L %s" % name)


def destruct_object(object_):
    """Destruct an object inheriting from TObject.

    See http://root.cern.ch/download/doc/ROOTUsersGuideHTML/ch19.html#d5e27551
    for more details

    Arguments:
        object_ (`ROOT.TObject`): Object to delete.

    """
    if issubclass(type(object_), ROOT.TObject):
        object_.IsA().Destructor(object_)


# Functional programming hack
def execute_and_return_self(obj, func, *args, **kwargs):
    """Execute a method and return the original object.

    This allows for a more functional programming style.

    Arguments:
        obj (object): Object to execute the method from.
        func (callable): Method to execute.
        *args, **kwargs: Arguments of the method.

    Returns:
        object: The input `obj`.

    """
    getattr(obj, func)(*args, **kwargs)
    return obj


# Helpers
def list_to_rooargset(iterable):
    """Convert a list into a RooArgSet.

    Arguments:
        iterable (iterable): Iterable to convert.

    Returns:
        `ROOT.RooArgSet`.

    """
    arg_set = ROOT.RooArgSet()
    for element in iterable:
        arg_set.add(element)
    return arg_set


def rooargset_to_set(rooargset):
    """Convert RooArgSet to a set.

    Arguments:
        rooargset (ROOT.RooArgSet): RooArgSet to convert.

    Returns:
        set

    """
    iter_ = rooargset.createIterator()
    output = set()
    while True:
        var = iter_.Next()
        if not var:
            return output
        output.add(var)

# EOF
