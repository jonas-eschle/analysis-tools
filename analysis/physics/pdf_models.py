#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   pdfs.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   28.02.2017
# =============================================================================
"""Basic PDFs to use for building complex factories."""


from functools import partial

import ROOT

from analysis.utils.pdf import load_pdf_by_name
from analysis.utils.root import execute_and_return_self
from analysis.physics.helpers import bind_to_object


# pylint: disable=R0903
class BifurcatedCBPdf(object):
    """Fit with a bifurcated CB.

    Parameter names, and their defaults (when applicable):
        - 'mu'
        - 'sigma'
        - 'alphaR'
        - 'nR'
        - 'alphaL'
        - 'nL'

    """

    PARAMETERS = ('mu',
                  'sigma',
                  'alphaR',
                  'nR',
                  'alphaL',
                  'nL')

    MANDATORY_PARAMETERS = ('mu',
                            'sigma',
                            'alphaR',
                            'nR',
                            'alphaL',
                            'nL')

    def get_pdf(self):
        """Get the physics PDF.

        Returns:
            BifurcatedCB.

        """
        return bind_to_object(self)(load_pdf_by_name('BifurcatedCB'))


class DoubleCBPdf(object):
    """Signal mass fit with the sum of two CB.

    Parameter names, and their defaults (when applicable):
        - 'mu' (5279.0)
        - 'sigma1'
        - 'alpha1'
        - 'n1'
        - 'sigma2'
        - 'alpha2'
        - 'n2'
        - 'frac'

    """

    PARAMETERS = ('mu',
                  'sigma1',
                  'alpha1',
                  'n1',
                  'sigma2',
                  'alpha2',
                  'n2',
                  'frac')

    MANDATORY_PARAMETERS = ('sigma1',
                            'alpha1',
                            'n1',
                            'sigma2',
                            'alpha2',
                            'n2',
                            'frac')

    PARAMETER_DEFAULTS = {'mu': 5279.0}

    def get_pdf(self):
        """Get the physics PDF.

        Returns:
            RooAddPdf: Sum of two `CBShape`.

        """
        return bind_to_object(self)(partial(lambda self, name, title, *inputs:
                                            ROOT.RooAddPdf(name, title,
                                                           self.get(name+'CB1',
                                                                    ROOT.RooCBShape(name+'CB1',
                                                                                    title+'CB1',
                                                                                    inputs[0],
                                                                                    *inputs[1:5])),
                                                           self.get(name+'CB2',
                                                                    ROOT.RooCBShape(name+'CB2',
                                                                                    title+'CB2',
                                                                                    inputs[0],
                                                                                    *((inputs[1],)+inputs[5:8]))),
                                                           inputs[8]),
                                            self))


class ExponentialPdf(object):
    """Exponential mass PDF.

    Parameter names:
        - 'tau'

    """

    PARAMETERS = ('tau', )

    MANDATORY_PARAMETERS = ('tau', )

    def get_pdf(self):
        """Get the physics PDF.

        Returns:
            RooExponential.

        """
        return bind_to_object(self)(ROOT.RooExponential)


class ArgusConvGaussPdf(object):
    """Partially reconstructed background mass PDF.

    It's built as the `RooFFTConvPdf` between a `RooArgusBG` and a `RooGaussian`.

    Parameter names:
        - 'threshold'
        - 'slope'
        - 'power'
        - 'mu'
        - 'sigma'

    """

    PARAMETERS = ('threshold',
                  'slope',
                  'power',
                  'mu',
                  'sigma')
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

    def get_pdf(self):
        """Get the convolved PDF.

        Returns a lambda function that will create the `RooFFTConvPdf` mimicking
        usual PDF instantiations.

        Note:
            The Argus and Gaussian PDFs are created new everytime the RooFFTConvPdf is
            instantiated.

        Returns:
            lambda.

        """
        return bind_to_object(self)(lambda name, title, buffer_fraction=self._buffer_fraction, *inputs:
                                    execute_and_return_self(ROOT.RooFFTConvPdf(name, title,
                                                                               inputs[0],
                                                                               ROOT.RooArgusBG(name+'Argus',
                                                                                               title+'Argus',
                                                                                               *inputs[:4]),
                                                                               ROOT.RooGaussian(name+'Resol',
                                                                                                title+'Resol',
                                                                                                inputs[0],
                                                                                                *inputs[4:])),
                                                            'setBufferFraction',
                                                            buffer_fraction))

# EOF
