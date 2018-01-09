#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   pdfs.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   28.02.2017
# =============================================================================
"""Basic PDFs to use for building complex factories."""
from __future__ import print_function, division, absolute_import


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

        Return:
            ROOT.RooGaussian.

        """
        return ROOT.RooGaussian(name, title,
                                *(self.get_observables()+self.get_fit_parameters()))


# pylint: disable=R0903
class CBPdfMixin(object):
    """Mixin defining a CB.

    Parameter names, and their defaults (when applicable):
        - 'mu'
        - 'sigma'
        - 'alpha'
        - 'n'

    """

    MANDATORY_PARAMETERS = ('mu',
                            'sigma',
                            'alpha',
                            'n')

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Return:
            ROOT.RooCBShape.

        """
        return ROOT.RooCBShape(name, title,
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

        Return:
            ROOT.BifurcatedCB.

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

        Return:
            ROOT.RooAddPdf: Sum of two `ROOT.CBShape`.

        """
        obs = self.get_observables()[0]
        params = self.get_fit_parameters()
        return ROOT.RooAddPdf(name, title,
                              self.set(name+'CB1',
                                       ROOT.RooCBShape(name+'CB1',
                                                       title+'CB1',
                                                       obs,
                                                       *params[0:4])),
                              self.set(name+'CB2',
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

        Return:
            ROOT.RooExponential.

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

    def __init__(self, config, parameters=None):
        """Configure the partially reconstructed background factory.

        Arguments:
            config (dict): PDF configuration. If it contains 'buffer_fraction', it is
              used to set the RooFFTConvPdf buffer fraction.

        """
        super(ArgusConvGaussPdfMixin, self).__init__(config, parameters)
        self._buffer_fraction = config.get('buffer_fraction', 1.0)

    def get_unbound_pdf(self, name, title):
        """Get the convolved PDF.

        Returns a lambda function that will create the `RooFFTConvPdf` mimicking
        usual PDF instantiations.

        Note:
            The Argus and Gaussian PDFs are created new every time the RooFFTConvPdf is
            instantiated.

        Return:
            lambda.

        """
        obs = self.get_observables()[0]
        params = self.get_fit_parameters()
        return execute_and_return_self(ROOT.RooFFTConvPdf(name, title,
                                                          obs,
                                                          self.set(name+'Argus',
                                                                   ROOT.RooArgusBG(name+'Argus',
                                                                                   title+'Argus',
                                                                                   obs,
                                                                                   *params[:3])),
                                                          self.set(name+'Resol',
                                                                   ROOT.RooGaussian(name+'Resol',
                                                                                    title+'Resol',
                                                                                    obs,
                                                                                    *params[3:]))),
                                       'setBufferFraction',
                                       self._buffer_fraction)


# pylint: disable=R0903
class IpatiaPdfMixin(object):
    """Mixin defining an Ipatia function.

    Parameter names, and their defaults (when applicable):
        - 'l'
        - 'zeta'
        - 'fb'
        - 'sigma'
        - 'mu'
        - 'a'
        - 'n'

    """

    MANDATORY_PARAMETERS = ('l',
                            'zeta',
                            'fb',
                            'sigma',
                            'mu',
                            'a',
                            'n')

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Return:
            ROOT.RooIpatia.

        """
        return load_pdf_by_name('RooIpatia', True)(name,
                                                   title,
                                                   *(self.get_observables()+self.get_fit_parameters()))


# pylint: disable=R0903
class Ipatia2PdfMixin(object):
    """Mixin defining an Ipatia2 function.

    Parameter names, and their defaults (when applicable):
        - 'l'
        - 'zeta'
        - 'fb'
        - 'sigma'
        - 'mu'
        - 'a'
        - 'n'
        - 'a2'
        - 'n2'

    """

    MANDATORY_PARAMETERS = ('l',
                            'zeta',
                            'fb',
                            'sigma',
                            'mu',
                            'a',
                            'n',
                            'a2',
                            'n2')

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Return:
            ROOT.RooIpatia2.

        """
        return load_pdf_by_name('RooIpatia2', True)(name,
                                                    title,
                                                    *(self.get_observables()+self.get_fit_parameters()))


class RooWorkspaceMixin(object):
    """Load a PDF from a RooWorkspace."""

    PARAMETERS = []

    def __init__(self, config, parameters=None):
        """Load the workspace.

        Raise:
            KeyError: On any errors.

        """
        super(RooWorkspaceMixin, self).__init__(config, parameters)
        try:
            workspace_path = config['workspace-path']
        except KeyError:
            raise KeyError("Workspace path ('workspace-path') is missing")
        try:
            workspace_name = config['workspace-name']
        except KeyError:
            raise KeyError("Workspace name ('workspace-name') is missing")
        # Load PDF
        try:
            pdf_name = config['workspace-pdf-name']
        except KeyError:
            raise KeyError("PDF name ('workspace-pdf-name') is missing")
        tfile = ROOT.TFile.Open(workspace_path)
        if not tfile:
            raise KeyError("Cannot open workspace file -> {}".format(workspace_path))
        workspace = tfile.Get(workspace_name)
        if not workspace:
            raise KeyError("Cannot get workspace from file -> {}".format(workspace_name))
        self._workspace = workspace
        pdf = workspace.pdf(pdf_name)
        if not pdf:
            raise KeyError("PDF cannot be found in workspace -> {}".format(pdf_name))
        self._workspace_pdf = pdf
        # Close the TFile
        tfile.Close()

    def get_observables(self):
        """Override the generic RooRealVars with objects from the RooWorkspace."""
        for obs_id, (obs_name, obs_title, obs_min, obs_max, unit) in self.OBSERVABLES.items():
            var = self._workspace.var(obs_name)
            if not var:
                raise KeyError("Observable {} not present in RooWorkspace".format(obs_name))
            if obs_id not in self or var != self[obs_id]:
                var.setStringAttribute('originalName',
                                       obs_id if obs_id not in self
                                       else self[obs_id].getStringAttribute('originalName'))
                self.set(obs_id, var)
                self.set_observable(obs_id, title=obs_title, limits=(obs_min, obs_max), units=unit)
        return super(RooWorkspaceMixin, self).get_observables()

    def get_unbound_pdf(self, name, title):
        """Get the RooKeysPdf.

        Returns a copy of the RooKeysPdf from the RooWorkspace.

        Return:
            ROOT.RooKeysPdf.

        """
        # Do proper observable replacement
        self.get_observables()
        pdf = self._workspace_pdf.Clone(name)
        pdf.SetTitle(title)
        return pdf

# EOF
