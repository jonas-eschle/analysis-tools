#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   root.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.01.2017
# =============================================================================
"""Utilities for interacting with ROOT."""
from __future__ import print_function, division, absolute_import

import os

import ROOT


def load_library(name, lib_dirs=None, debug=False, force=False, use_mathmore=False):
    """Load C++ ROOT libraries, compiling if necessary.

    Libraries are looked for first in the current folder or `lib_dir`.
    If an absolute path is specified, it takes priority.

    Arguments:
        name (str): Name of the library to load (.cxx not needed).
        lib_dirs (list, optional): Folders storing the library sources.
        debug (bool, optional): Compile the library en debug mode? Defaults
            to `False`.
        force (bool, optional): Force recompilation? Defaults to `False`.
        use_mathmore (bool, optional): Load libMathMore before compiling. Defaults
            to False.

    Return:
        bool: Was the operation successful?

    """
    if name.endswith('+'):
        name = name.split('+')[0]
    lib_dirs = lib_dirs if lib_dirs else []
    # Determine file to load
    for extension in ('.cc', '.cxx'):
        if not os.path.splitext(name)[1]:
            file_name = name + extension
        else:
            file_name = name
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
        raise OSError("Cannot locate library -> {}".format(name))
    options = 'k'
    if force:
        options += "f"
    if debug:
        options += "g"
    if use_mathmore:
        ROOT.gSystem.Load('libMathMore')
    if not ROOT.gSystem.CompileMacro(name, options):
        return False
    ROOT.gSystem.Load(name.replace('.c', '_c'))
    return True


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

    Return:
        object: The input `obj`.

    """
    getattr(obj, func)(*args, **kwargs)
    return obj


# Helpers
def list_to_rooabscollection(iterable, collection_type):
    """Convert a list into a RooAbsCollection.

    Arguments:
        iterable (iterable): Iterable to convert.
        collection_type (ROOT.RooAbsCollection): Type of collection to
            convert to.

    Return:
        `collection_type`.

    """
    collection = collection_type()
    for element in iterable:
        if element:
            collection.add(element)
    return collection


def list_to_rooarglist(iterable):
    """Convert a list into a RooArgList.

    Arguments:
        iterable (iterable): Iterable to convert.

    Return:
        `ROOT.RooArgList`.

    """
    return list_to_rooabscollection(iterable, ROOT.RooArgList)


def list_to_rooargset(iterable):
    """Convert a list into a RooArgSet.

    Arguments:
        iterable (iterable): Iterable to convert.

    Return:
        `ROOT.RooArgSet`.

    """
    return list_to_rooabscollection(iterable, ROOT.RooArgSet)


def iterate_roocollection(collection):
    """Iterate a RooAbsCollection object.

    Arguments:
        collection (ROOT.RooAbsCollection): Object to iterate.

    Yields:
        ROOT.TObject: Object inside the collection.

    """
    iter_ = collection.createIterator()
    while True:
        var = iter_.Next()
        if not var:
            raise StopIteration
        yield var


def rooargset_to_set(rooargset):
    """Convert RooArgSet to a set.

    Arguments:
        rooargset (ROOT.RooArgSet): RooArgSet to convert.

    Return:
        set

    """
    return {var for var in iterate_roocollection(rooargset)}


def rooarglist_to_list(rooarglist):
    """Convert RooArgList to a list.

    Arguments:
        rooarglist (ROOT.RooArgList): RooArgList to convert.

    Return:
        list

    """
    return [var for var in iterate_roocollection(rooarglist)]


def copy_tree_with_cuts(old_file, tree_name, new_file_name, cuts, active_branches=["*"], disabled_branches=None):
    """Copy a TTree for a file applying cuts.

    The names of the branches to copy, ie, active, can be specified
    to reduce file size.

    Arguments:
        old_file (str): File name to copy the structure from.
        tree_name (str): Name of the tree to analyze.
        new_file_name (str): Name of the file to create.
        cuts (list): Cuts to apply. A string can be given too.
        active_branches (list, optional): Branches to pass on to the new tree. Defaults to all.
        disabled_branches (list, optional): Branches to disable after activating. Defaults to None.

    Raise:
        AttributeError: When the cuts variable cannot be used to apply cuts.
        ValueError: When there are no events left after the cuts.
        KeyError: When the input tree doesn't exist.

    """

    def copy_file_structure(old_file, tree_name, new_file):
        """Copy the structure of a ROOT file.

        Arguments:
            old_file (str): File name to copy the structure from.
            tree_name (str): Name of the tree to analyze.
            new_file (str): Name of the file to create.

        Return:
            tuple: old TFile, old TTree, new TFile.

        Raise:
            KeyError: If the tree doesn't exist.

        """
        old_file = ROOT.TFile.Open(old_file)
        old_tree = old_file.Get(tree_name)
        if not old_tree:
            raise KeyError("Cannot find tree -> %s" % tree_name)
        new_file = ROOT.TFile.Open(new_file, 'RECREATE')
        dirs = tree_name.split('/')
        if len(dirs) > 1:
            for dir_ in dirs[:-1]:
                new_file.mkdir(dir_)
                new_file.cd(dir_)
        return old_file, old_tree, new_file

    try:
        old_file, old_tree, new_file = copy_file_structure(old_file, tree_name, new_file_name)
    except KeyError:
        raise
    # Process cuts
    if isinstance(cuts, (list, tuple)):
        cut_string = ' && '.join(cuts)
    elif isinstance(cuts, str):
        cut_string = cuts
    elif isinstance(cuts, ROOT.TCut):
        cut_string = cuts.GetTitle()
    else:
        raise AttributeError
    # Which branches to save?
    old_tree.SetBranchStatus("*", 0)
    for branch in active_branches:
        old_tree.SetBranchStatus(branch, 1)
    if disabled_branches:
        for branch in disabled_branches:
            old_tree.SetBranchStatus(branch, 0)
    # Let's do it
    new_tree = old_tree.CopyTree(cut_string)
    if not new_tree:
        raise ValueError("No events passed the selection")
    new_tree.Write("", ROOT.TObject.kOverwrite)
    new_file.Write("", ROOT.TObject.kOverwrite)
    new_file.Close()
    old_file.Close()

# EOF
