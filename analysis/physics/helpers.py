#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   helpers.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   31.01.2017
# =============================================================================
"""Helper classes to aid in the construction of Physics Factories."""

import functools
import operator

import ROOT


def build_factory_prod(factories):
    """Build a Product PDF from the given factories.

    A partial function is returned, which can be used to instantiate
    a `RooProfPdf` mimicking the interface of a `PhysicsFactory`.

    Arguments:
        factories (list): Physics factories to do the product of.

    Returns:
        `functools.partial`: Prepared RooProdPdf creator.

    """
    def accumulate(iterable, func=operator.add):
        """Accumulate list.

        Arguments:
            iterable (iterable): Object to accumulate.
            func (callable, optional): Accumulation function. Defaults
                to addition through `operator.add`.

        Examples:

            >>> accumulate([1,2,3,4,5]) --> 1 3 6 10 15
            >>> accumulate([1,2,3,4,5], operator.mul) --> 1 2 6 24 120

        """
        iter_ = iter(iterable)
        total = next(iter_)
        yield total
        for element in iter_:
            total = func(total, element)
            yield total

    def do_build(factories, name, title, *inputs):
        """Instantiate the RooProdPdf.

        The PDFs used to build it are also instantiated.

        Arguments:
            factories (list): Physics factories to do the product of.
            name (str): Name of the PDF.
            title (str): Title of the PDF.
            *inputs (list): Arguments of the intermediate PDF instantiation.
                This includes the observables and the fit parameters of each
                of them.

        """
        obs_num = [0] + list(accumulate([len(factory.get_observables())
                                         for factory in factories]))
        param_num = [0] + list(accumulate([len(factory.get_fit_parameters())
                                           for factory in factories]))
        pdfs = ROOT.RooArgList()
        for pdf_num, factory in enumerate(factories):
            pdfs.add(factory.get_pdf()("%s_%s" % (name, pdf_num), "%s_%s" % (title, pdf_num),
                                       *(inputs[obs_num[pdf_num]:obs_num[pdf_num+1]] +
                                         inputs[obs_num[-1]+param_num[pdf_num]:obs_num[-1]+param_num[pdf_num+1]])))
        return ROOT.RooProdPdf(name, title, pdfs)
    return functools.partial(do_build, factories)


def bind_to_object(obj):
    """Make sure a copy of the object is kept when creating it."""
    def partial_wrapper(func):
        """Wrap the function we want to bind."""
        def func_wrapper(*args):
            """Execute the creation function if the object doesn't exist."""
            return functools.partial(lambda self, name, *arglist:
                                     self.get(name, func(name, *arglist)),
                                     obj)(*args)
        return func_wrapper
    return partial_wrapper

# EOF
