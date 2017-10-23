#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   test_fit.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   11.07.2017
# =============================================================================
"""Test the fit module."""
from __future__ import print_function, division, absolute_import

import pytest

import ROOT

from analysis.fit.result import FitResult
from analysis.utils.logging_color import get_logger


get_logger('analysis.fit').setLevel(10)


@pytest.fixture
def fit_result():
    """Create a gaussian and fit it."""
    # Variables
    x = ROOT.RooRealVar("x", "x", -10, 10)
    mu = ROOT.RooRealVar("mu", "mu", 0)
    sigma = ROOT.RooRealVar("sigma", "sigma", 0.5, 2.5)
    yield_ = ROOT.RooRealVar("yield", "yield", 50, 10, 100)
    # PDFs
    gauss = ROOT.RooGaussian("gauss", "gauss", x, mu, sigma)
    gauss_ext = ROOT.RooExtendPdf("gauss_ext", "gauss_ext", gauss, yield_)
    # Dataset
    dataset = gauss.generate(ROOT.RooArgSet(x), 50)
    # Fit
    return gauss_ext.fitTo(dataset,
                           ROOT.RooFit.Save(True),
                           ROOT.RooFit.Extended(True),
                           ROOT.RooFit.Minos(True))


# pylint: disable=W0621
def test_fitresult_convergence(fit_result):
    """Test fit result convergence."""
    assert FitResult.from_roofit(fit_result).has_converged()


# pylint: disable=W0621
def test_fitresult_yaml_conversion(fit_result):
    """Test YAML conversion."""
    res = FitResult.from_roofit(fit_result)
    res_conv = FitResult.from_yaml(res.to_yaml())
    assert (res_conv.get_covariance_matrix() == res.get_covariance_matrix()).all()


# EOF
