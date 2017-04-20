#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   pdfs.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   28.02.2017
# =============================================================================
"""Basic PDFs to use for building complex factories."""


import ROOT

from analysis.utils.pdf import load_pdf_by_name
from analysis.utils.root import execute_and_return_self


# pylint: disable=R0903
class GaussianPdfMixin(object):
    """Mixin defining a Gaussian.

    Parameter names, and their defaults (when applicable):
        - 'mu'
        - 'sigma'

    """

    MANDATORY_PARAMETERS = ('mu',
                            'sigma')

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Returns:
            BifurcatedCB.

        """
        return ROOT.RooGaussian(name, title,
                                *(self.get_observables()+self.get_fit_parameters()))


# pylint: disable=R0903
class BifurcatedCBPdfMixin(object):
    """Mixin defining a bifurcated CB.

    Parameter names, and their defaults (when applicable):
        - 'mu'
        - 'sigma'
        - 'alphaR'
        - 'nR'
        - 'alphaL'
        - 'nL'

    """

    MANDATORY_PARAMETERS = ('mu',
                            'sigma',
                            'alphaR',
                            'nR',
                            'alphaL',
                            'nL')

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Returns:
            BifurcatedCB.

        """
        return load_pdf_by_name('BifurcatedCB')(name,
                                                title,
                                                *(self.get_observables()+self.get_fit_parameters()))


# pylint: disable=R0903
class DoubleCBPdfMixin(object):
    """Signal mass fit with the sum of two CB.

    Parameter names, and their defaults (when applicable):
        - 'mu'
        - 'sigma1'
        - 'alpha1'
        - 'n1'
        - 'sigma2'
        - 'alpha2'
        - 'n2'
        - 'frac'

    """

    MANDATORY_PARAMETERS = ('mu',
                            'sigma1',
                            'alpha1',
                            'n1',
                            'sigma2',
                            'alpha2',
                            'n2',
                            'frac')

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Returns:
            RooAddPdf: Sum of two `CBShape`.

        """
        obs = self.get_observables()[0]
        params = self.get_fit_parameters()
        return ROOT.RooAddPdf(name, title,
                              self.get(name+'CB1',
                                       ROOT.RooCBShape(name+'CB1',
                                                       title+'CB1',
                                                       obs,
                                                       *params[0:4])),
                              self.get(name+'CB2',
                                       ROOT.RooCBShape(name+'CB2',
                                                       title+'CB2',
                                                       obs,
                                                       *((params[0],)+params[4:7]))),
                              params[7])


# pylint: disable=R0903
class ExponentialPdfMixin(object):
    """Exponential mass PDF.

    Parameter names:
        - 'tau'

    """

    MANDATORY_PARAMETERS = ('tau', )

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Returns:
            RooExponential.

        """
        return ROOT.RooExponential(name, title,
                                   *(self.get_observables()+self.get_fit_parameters()))


# pylint: disable=R0903
class ArgusConvGaussPdfMixin(object):
    """Partially reconstructed background mass PDF.

    It's built as the `RooFFTConvPdf` between a `RooArgusBG` and a `RooGaussian`.

    Parameter names:
        - 'threshold'
        - 'slope'
        - 'power'
        - 'mu'
        - 'sigma'

    """

    MANDATORY_PARAMETERS = ('threshold',
                            'slope',
                            'power',
                            'mu',
                            'sigma')

    def __init__(self, **config):
        """Configure the partially reconstructed background factory.

        Arguments:
            **config (dict): PDF configuration. If it contains 'buffer_fraction', it is
                used to set the RooFFTConvPdf buffer fraction.

        """
        self._buffer_fraction = config.get('buffer_fraction', 1.0)

    def get_unbound_pdf(self, name, title):
        """Get the convolved PDF.

        Returns a lambda function that will create the `RooFFTConvPdf` mimicking
        usual PDF instantiations.

        Note:
            The Argus and Gaussian PDFs are created new everytime the RooFFTConvPdf is
            instantiated.

        Returns:
            lambda.

        """
        obs = self.get_observables()[0]
        params = self.get_fit_parameters()
        return execute_and_return_self(ROOT.RooFFTConvPdf(name, title,
                                                          obs,
                                                          ROOT.RooArgusBG(name+'Argus',
                                                                          title+'Argus',
                                                                          obs,
                                                                          *(params[:3] +
                                                                            ROOT.RooGaussian(name+'Resol',
                                                                                             title+'Resol',
                                                                                             obs,
                                                                                             *params[4:])))),
                                       'setBufferFraction',
                                       self._buffer_fraction)

# EOF
