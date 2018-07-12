#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   test_physics.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   19.04.2017
# =============================================================================
"""Test imports."""
from __future__ import print_function, division, absolute_import

import yaml
import yamlloader
import pytest

import ROOT

import analysis.physics as phys
import analysis.physics.factory as phys_factory
import analysis.physics.pdf_models as pdfs
from analysis.utils.logging_color import get_logger
from analysis.utils.exceptions import ConfigError


get_logger('analysis.physics').setLevel(10)


# Define a few factories
# pylint: disable=W0223
class MassFactory(phys_factory.PhysicsFactory):
    """Abstract base class for mass fits.

    Implements the observables.

    """

    OBSERVABLES = (('mass', 'mass', 5000, 5500, "MeV/c^{2}"),)


class DoubleCBFactory(pdfs.DoubleCBPdfMixin, MassFactory):
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


class ExponentialFactory(pdfs.ExponentialPdfMixin, MassFactory):
    """Exponential mass PDF.

    Parameter names:
        - 'tau'

    """


class FlatQ2(phys_factory.PhysicsFactory):
    """Abstract base class for q2 PDFs.

    Implements the observable.

    """

    OBSERVABLES = (('q2', 'q2', 1, 19, "GeV^{2}/c^{4}"),)

    PARAMETERS = ('const', )

    PARAMETER_DEFAULTS = {'const': 1.0}

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Returns a lambda that builds the `RooPolynomial` starting from
            order 0.

        Return:
            lambda.

        """
        fit_parameters = ROOT.RooArgList(self.get_fit_parameters()[0])
        return ROOT.RooPolynomial(name, title,
                                  self.get_observables()[0],
                                  fit_parameters,
                                  0)


# Register them
phys.register_physics_factories("mass", {'cb': DoubleCBFactory,
                                         'exp': ExponentialFactory})
phys.register_physics_factories("q2", {'flat': FlatQ2})


# A helper
def load_model(config_str):
    """Load a model using `configure_model`."""
    factory_config = yaml.load(config_str,
                               Loader=yamlloader.ordereddict.CLoader)
    return phys.configure_model(factory_config)


@pytest.fixture
def factory():
    """Load a PhysicsFactory."""
    return load_model("""mass:
    pdf: cb
    parameters:
        mu: 5246.7 5200 5300
        sigma1: '@sigma/sigma/sigma/41 35 45'
        sigma2: '@sigma'
        n1: 5.6689 2 9
        n2:  1.6 0.2 2
        alpha1: 0.25923 0.1 0.5
        alpha2:  -1.9749 -3.5 -1.0
        frac: 0.84873 0.1 1.0""")


@pytest.fixture
def factory_with_yield():
    """Load a PhysicsFactory with yield."""
    return load_model("""mass:
    pdf: cb
    yield: 1000 300 2000
    parameters:
        mu: 5246.7 5200 5300
        sigma1: '@sigma/sigma/sigma/41 35 45'
        sigma2: '@sigma'
        n1: 5.6689 2 9
        n2: 1.6 0.2 2
        alpha1: 0.25923 0.1 0.5
        alpha2: -1.9749 -3.5 -1.0
        frac: 0.84873 0.1 1.0""")


@pytest.fixture
def factory_with_blind_yield():
    """Load a PhysicsFactory with blinded yield."""
    return load_model("""mass:
    pdf: cb
    yield: 'BLIND @yield1 yieldstr 18 94'
    parameters:
        mu: 5246.7 5200 5300
        sigma1: '@sigma/sigma/sigma/41 35 45'
        sigma2: '@sigma'
        shared_yield: '@yield1/Yield/Yield/VAR 1000 300 2000'
        alpha_shared: '@alpha_blind/alpha_blind/alpha_blind/VAR 0.25923 0.1 0.5'
        n1: 5.6689 2 9
        n2: 1.6 0.2 2
        alpha1: 'BLIND @alpha_blind mystr 10 50'
        alpha2: '-1.9749 -3.5 -1.0'
        frac: 0.84873 0.1 1.0""")


# pylint: disable=W0621
def test_factory_load(factory):
    """Test factory loading returns an object of the correct type."""
    return isinstance(factory, phys_factory.PhysicsFactory)


# pylint: disable=W0621
def test_factory_get_pdf(factory):
    """Test the PDF from the factory has the correct properties."""
    model = factory.get_pdf("TestFactory", "TestFactory")
    assert isinstance(model, ROOT.RooAddPdf)
    assert model.GetName() == 'TestFactory'
    assert model.GetTitle() == 'TestFactory'


# pylint: disable=W0621
def test_factory_get_extendedpdf(factory, factory_with_yield):
    """Test the PDF from the factory has the correct properties."""
    model = factory.get_extended_pdf("TestFactory", "TestFactory", 1000)
    model_yield = factory_with_yield.get_extended_pdf("TestFactoryWithYield", "TestFactoryWithYield")
    assert model.getVariables()["Yield"].getVal() == 1000.0


# pylint: disable=W0621
def test_factory_get_extendedpdf_blind(factory, factory_with_blind_yield):
    """Test the PDF from the factory has the correct properties."""
    model = factory.get_extended_pdf("TestFactory", "TestFactory", 1000)
    model_yield = factory_with_blind_yield.get_extended_pdf("TestFactoryWithBlindYield",
                                                            "TestFactoryWithBlindYield")

    print("value from direct rooRealVar", factory_with_blind_yield.get_fit_parameters()[2].getVariables()['alpha_blind'].getVal())
    print("Hidden value", factory_with_blind_yield.get_fit_parameters()[2].getHiddenVal())

    assert factory_with_blind_yield.get_fit_parameters()[2].getVariables()['alpha_blind'].getMax() == 0.5
    assert factory_with_blind_yield.get_fit_parameters()[2].getVariables()['alpha_blind'].getMin() == 0.1
    assert isinstance(factory_with_blind_yield.get_fit_parameters()[2].getVariables()['alpha_blind'],
                      ROOT.RooRealVar)
    assert isinstance(factory_with_blind_yield.get_fit_parameters()[2], ROOT.RooUnblindPrecision)

    assert isinstance(factory_with_blind_yield.get_yield_var(), ROOT.RooUnblindPrecision)
    assert isinstance(factory_with_blind_yield.get_yield_var().getVariables()['Yield'], ROOT.RooRealVar)
    assert factory_with_blind_yield.get_yield_var().getVariables()['Yield'].getMax() == 2000
    assert factory_with_blind_yield.get_yield_var().getVariables()['Yield'].getMin() == 300


# pylint: disable=W0621
def test_factory_shared(factory):
    """Test that shared parameters are treated correctly."""
    model = factory.get_pdf("TestFactory", "TestFactory")
    sigma1 = model.getComponents()['TestFactoryCB1'].getVariables()['sigma']
    sigma2 = model.getComponents()['TestFactoryCB2'].getVariables()['sigma']
    assert sigma1 == sigma2
    assert sigma2.getVal() == 41.0
    assert sigma2.getMin() == 35.0
    assert sigma2.getMax() == 45.0


@pytest.fixture
def prod_factory():
    """Load a ProdPhysicsFactory."""
    return load_model("""
yield: GAUSS 999 100
pdf:
    mass:
        pdf: cb
        parameters:
            mu: 5246.7 5200 5300
            sigma1: '@sigma/sigma/sigma/41 35 45'
            sigma2: '@sigma'
            n1: 5.6689 2 9
            n2: 1.6 0.2 2
            alpha1: 0.25923 0.1 0.5
            alpha2: -1.9749 -3.5 -1.0
            frac: 0.84873 0.1 1.0
    q2:
        pdf: flat
        parameters:
            const: '@sigma'
""")


# pylint: disable=W0621
def test_prodfactory_load(prod_factory):
    """Test factory loading returns an object of the correct type."""
    assert isinstance(prod_factory, phys_factory.ProductPhysicsFactory)
    assert isinstance(prod_factory.get_constraints()['YieldConstraint'], ROOT.RooGaussian)


# pylint: disable=W0621
def test_prodfactory_get_pdf(prod_factory):
    """Test the PDF from the product factory has the correct properties."""
    model = prod_factory.get_pdf("TestProdFactory", "TestProdFactory")
    assert isinstance(model, ROOT.RooProdPdf)
    assert model.GetName() == 'TestProdFactory'
    assert model.GetTitle() == 'TestProdFactory'
    assert model.getVariables()['mu^{mass}'].getVal() == 5246.7  # Checks naming convention


# pylint: disable=W0621,C0103
def test_prodfactory_get_extendedpdf(prod_factory):
    """Test the PDF from the product factory has the correct properties."""
    model = prod_factory.get_extended_pdf("TestProdFactory", "TestProdFactory")
    assert model.getVariables()["Yield"].getVal() == 999.0


# pylint: disable=W0621
def test_prodfactory_shared(prod_factory):
    """Test that shared parameters are treated correctly."""
    model = prod_factory.get_pdf("TestProdFactory", "TestProdFactory")
    model.getComponents()['TestProdFactory^{mass}CB1'].getVariables().Print("v")
    sigma1 = model.getComponents()['TestProdFactory^{mass}CB1'].getVariables()['sigma']
    sigma2 = model.getComponents()['TestProdFactory^{mass}CB2'].getVariables()['sigma']
    const = model.getComponents()['TestProdFactory^{q2}'].getVariables()['sigma']
    assert sigma1 == sigma2
    assert sigma1 == const
    assert sigma2.getVal() == 41.0
    assert sigma2.getMin() == 35.0
    assert sigma2.getMax() == 45.0


def test_prodfactory_error():
    """Test if a badly configured ProdFactory is picked up."""
    try:
        load_model("""
yield: GAUSS 999 100
pdf:
    mass:
        pdf: cb
        yield: GAUSS 999 100
        parameters:
            mu: 5246.7 5200 5300
            sigma1: '@sigma/sigma/sigma/41 35 45'
            sigma2: '@sigma'
            n1: 5.6689 2 9
            n2: 1.6 0.2 2
            alpha1: 0.25923 0.1 0.5
            alpha2: -1.9749 -3.5 -1.0
            frac: 0.84873 0.1 1.0
    q2:
        pdf: flat
        parameters:
            const: '@sigma'
""")
    except ConfigError:
        pass
    else:
        assert False


@pytest.fixture
def sum_factory():
    """Load a SumPhysicsFactory."""
    return load_model("""
signal:
    yield: '@yield/yield/yield/GAUSS 999 100'
    pdf:
        mass:
            pdf: cb
            parameters:
                mu: 5246.7 5200 5300
                sigma1: '@sigma/sigma/sigma/41 35 45'
                sigma2: '@sigma'
                n1: 5.6689 2 9
                n2: 1.6 0.2 2
                alpha1: 0.25923 0.1 0.5
                alpha2: -1.9749 -3.5 -1.0
                frac: 0.84873 0.1 1.0
background:
    yield: '@yield'
    pdf:
        mass:
            pdf: exp
            parameters:
                tau: CONST -0.003
""")


@pytest.fixture
def sum_factory_frac():
    """Load a SumPhysicsFactory."""
    return load_model("""
signal:
    yield: 0.5
    pdf:
        mass:
            pdf: cb
            parameters:
                mu: 5246.7 5200 5300
                sigma1: '@sigma/sigma/sigma/41 35 45'
                sigma2: '@sigma'
                n1: 5.6689 2 9
                n2: 1.6 0.2 2
                alpha1: 0.25923 0.1 0.5
                alpha2: -1.9749 -3.5 -1.0
                frac: 0.84873 0.1 1.0
background:
    pdf:
        mass:
            pdf: exp
            parameters:
                tau: CONST -0.003
""")


@pytest.fixture
def sum_factory_ratio():
    """Load a SumPhysicsFactory with a RATIO."""
    return load_model("""
signal:
    yield: '@yield/yield/yield/GAUSS 999 100'
    pdf:
        mass:
            pdf: cb
            parameters:
                mu: 5246.7 5200 5300
                sigma1: '@sigma/sigma/sigma/41 35 45'
                sigma2: '@sigma'
                n1: 5.6689 2 9
                n2: 1.6 0.2 2
                alpha1: 0.25923 0.1 0.5
                alpha2: -1.9749 -3.5 -1.0
                frac: 0.84873 0.1 1.0
background:
    yield: 'RATIO @yield 2'
    pdf:
        mass:
            pdf: exp
            parameters:
                tau: CONST -0.003
""")


# pylint: disable=W0621
def test_sumfactory_load(sum_factory):
    """Test factory loading returns an object of the correct type."""
    assert isinstance(sum_factory, phys_factory.SumPhysicsFactory)
    # Is the constraint loaded properly?
    assert isinstance(sum_factory.get_constraints()['yieldConstraint'],
                      ROOT.RooGaussian)
    # Is the constraint propagated properly?
    assert sum_factory.get_constraints()['yieldConstraint'] == \
        sum_factory.get_children()['background'].get_constraints()['yieldConstraint']


# pylint: disable=W0621
def test_sumfactory_get_extendedpdf(sum_factory):
    """Test the PDF from the product factory has the correct properties."""
    model = sum_factory.get_extended_pdf("TestSumFactory", "TestSumFactory")
    assert isinstance(model, ROOT.RooAddPdf)
    assert model.GetName() == 'TestSumFactory'
    assert model.GetTitle() == 'TestSumFactory'
    assert model.getVariables()["tau^{background}"].getVal() == -0.003
    assert model.getVariables()["tau^{background}"].isConstant()


# pylint: disable=W0621
def test_sumfactory_shared(sum_factory):
    """Test that shared parameters are treated correctly."""
    model = sum_factory.get_extended_pdf("TestSumFactory", "TestSumFactory")
    yield_signal = model.getComponents()['TestSumFactory^{signal}'].getVariables()['yield']
    yield_background = model.getComponents()['TestSumFactory^{background}'].getVariables()['yield']
    assert yield_signal == yield_background
    assert yield_signal.getVal() == 999


def test_sumfactory_fractions(sum_factory_frac):
    """Test that the sum works well with fractions."""
    model = sum_factory_frac.get_extended_pdf("TestSumFactory", "TestSumFactory", 1000)
    frac_signal = model.getVariables()['Fraction^{signal}']
    frac_background = sum_factory_frac.get_children()['background'].get('Fraction')
    assert frac_signal.getVal() + frac_background.getVal() == 1.0
    assert sum_factory_frac.get_yield_var().getVal() == 1000.0
    assert sum_factory_frac.get_children()['signal'].get_yield_var().getVal() == 500.0
    frac_signal.setVal(0.7)
    assert frac_signal.getVal() + frac_background.getVal() == 1.0
    assert sum_factory_frac.get_children()['signal'].get_yield_var().getVal() == 700.0


def test_sumfactory_ratio_load(sum_factory_ratio):
    """Test that ratios are working."""
    assert sum_factory_ratio.get_children()['signal'].get_yield_var().getVal() == \
        2.0 * sum_factory_ratio.get_children()['background'].get_yield_var().getVal()


@pytest.fixture
def sim_factory():
    """Load a SimultaneousPhysicsFactory."""
    return load_model("""
categories:
    - TestCat
pdf:
    label1:
        signal:
            yield: 999
            pdf:
                mass:
                    pdf: cb
                    parameters:
                        mu: 5246.7 5200 5300
                        sigma1: '@sigma/sigma/sigma/41 35 45'
                        sigma2: '@sigma'
                        n1: 5.6689 2 9
                        n2: 1.6 0.2 2
                        alpha1: 0.25923 0.1 0.5
                        alpha2: -1.9749 -3.5 -1.0
                        frac: 0.84873 0.1 1.0
                q2:
                    pdf: flat
                    parameters:
                        const: '@sigma'
        background:
            yield: 320
            pdf:
                mass:
                    pdf: exp
                    parameters:
                        tau: CONST -0.003
                q2:
                    pdf: flat
                    parameters:
                        const: '@sigma'
    label2:
        signal:
            yield: 231
            pdf:
                mass:
                    pdf: cb
                    parameters:
                        mu: 5246.7 5200 5300
                        sigma1: '@sigma'
                        sigma2: '@sigma'
                        n1: 5.6689 2 9
                        n2: 1.6 0.2 2
                        alpha1: 0.25923 0.1 0.5
                        alpha2: -1.9749 -3.5 -1.0
                        frac: 0.84873 0.1 1.0
""")


# pylint: disable=W0621
def test_simfactory_load(sim_factory):
    """Test factory loading returns an object of the correct type."""
    assert isinstance(sim_factory, phys_factory.SimultaneousPhysicsFactory)


# pylint: disable=W0621
def test_simfactory_get_pdf(sim_factory):
    """Test the PDF from the product factory has the correct properties."""
    model = sim_factory.get_extended_pdf("TestSimFactory", "TestSimFactory")
    assert isinstance(model, ROOT.RooSimultaneous)
    assert model.GetName() == 'TestSimFactory'
    assert model.GetTitle() == 'TestSimFactory'
    assert model.getVariables()["tau^{label1;background;mass}"].getVal() == -0.003
    assert model.getVariables()["tau^{label1;background;mass}"].isConstant()


# pylint: disable=W0621
def test_simfactory_vs_factory(factory, sim_factory):
    """Compare that the same configuration gives the same object."""
    fac_model = factory.get_pdf("TestFactory", "TestFactory")
    sim_model = sim_factory.get_extended_pdf("TestSimFactory", "TestSimFactory")
    factory.get_observables()[0].setVal(5000.0)
    sim_factory.get_observables()[0].setVal(5000.0)
    assert fac_model.getVal() == sim_model.getComponents()["TestSimFactory^{label1;signal;mass}_{noext}"].getVal()


@pytest.fixture
def shift_scale_factory():
    """Load a PhysicsFactory."""
    return load_model("""mass:
    pdf: cb
    parameters:
        mu: SHIFT @shift_mu @muMC
        shift_mu: '@shift_mu/shift_mu/shift_mu/VAR 41 35 45'
        muMC: '@muMC/muMC/muMC/CONST 5100'
        sigmaMC: '@sigmaMC/sigmaMC/sigmaMC/CONST 4'
        scale_sigma1: '@scale_sigma1/scale_sigma1/scale_sigma1/VAR 2 0.1 5'
        sigma1: 'SCALE @scale_sigma1 @sigmaMC'
        scale_sigma2: '@scale_sigma2/scale_sigma2/scale_sigma2/VAR 3 0.2 4'
        sigma2: 'SCALE @scale_sigma2 42'
        shift_n1: '@shift_n1/shift_n1/shift_n1/VAR 4 3 5'
        n1: 'SHIFT @shift_n1 5.6689'
        n2:  1.6 0.2 2
        alpha1: 0.25923 0.1 0.5
        alpha2:  -1.9749 -3.5 -1.0
        frac: 0.84873 0.1 1.0""")


@pytest.fixture
def arithmetics_factory():
    """Load a PhysicsFactory."""
    return load_model("""mass:
    pdf: cb
    parameters:
        mu: ARITHMETICS 23*2/2
        shift_mu: '@shift_mu/shift_mu/shift_mu/VAR 41 35 45'
        muMC: '@muMC/muMC/muMC/CONST 5100'
        sigmaMC: '@sigmaMC/sigmaMC/sigmaMC/CONST 4'
        scale_sigma1: '@scale_sigma1/scale_sigma1/scale_sigma1/VAR 2 0.1 5'
        sigma1: 'SCALE @scale_sigma1 @sigmaMC'
        scale_sigma2: '@scale_sigma2/scale_sigma2/scale_sigma2/VAR 3 0.2 4'
        sigma2: 'SCALE @scale_sigma2 42'
        shift_n1: '@shift_n1/shift_n1/shift_n1/VAR 4 3 5'
        n1: 'SHIFT @shift_n1 5.6689'
        n2:  1.6 0.2 2
        alpha1: 0.25923 0.1 0.5
        alpha2:  -1.9749 -3.5 -1.0
        frac: 0.84873 0.1 1.0""")


# in the Kstee angular analysis, there are several config files which use a different
# syntax than expected. As RooAddition and RooMultiplication
@pytest.fixture
def legacy_syntax_factory():
    """Load a PhysicsFactory."""
    return load_model("""mass:
    pdf: cb
    parameters:
        mu: SHIFT @muMC @shift_mu"""  # intentionally inverted syntax
        """
        shift_mu: '@shift_mu/shift_mu/shift_mu/VAR 41 35 45'
        muMC: '@muMC/muMC/muMC/CONST 5100'
        sigmaMC: '@sigmaMC/sigmaMC/sigmaMC/CONST 4'
        scale_sigma1: '@scale_sigma1/scale_sigma1/scale_sigma1/VAR 2 0.1 5'
        sigma1: 'SCALE @sigmaMC @scale_sigma1'"""  # intentionally inverted syntax
        """
        scale_sigma2: '@scale_sigma2/scale_sigma2/scale_sigma2/VAR 3 0.2 4'
        sigma2: 'SCALE @scale_sigma2 42'
        shift_n1: '@shift_n1/shift_n1/shift_n1/VAR 4 3 5'
        n1: 'SHIFT @shift_n1 5.6689'
        n2:  1.6 0.2 2
        alpha1: 0.25923 0.1 0.5
        alpha2:  -1.9749 -3.5 -1.0
        frac: 0.84873 0.1 1.0""")


def scale_shift_tester(factory):

    assert isinstance(factory.get_fit_parameters()[0], ROOT.RooAddition)
    assert isinstance(factory.get_fit_parameters()[0].getVariables()["shift_mu"], ROOT.RooRealVar)
    assert isinstance(factory.get_fit_parameters()[0].getVariables()["muMC"], ROOT.RooRealVar)

    assert isinstance(factory.get_fit_parameters()[3], ROOT.RooAddition)
    assert isinstance(factory.get_fit_parameters()[3].getVariables()["shift_n1"], ROOT.RooRealVar)

    assert isinstance(factory.get_fit_parameters()[1], ROOT.RooProduct)
    assert isinstance(factory.get_fit_parameters()[1].getVariables()["scale_sigma1"], ROOT.RooRealVar)
    assert isinstance(factory.get_fit_parameters()[1].getVariables()["sigmaMC"], ROOT.RooRealVar)

    assert isinstance(factory.get_fit_parameters()[4], ROOT.RooProduct)
    assert isinstance(factory.get_fit_parameters()[4].getVariables()["scale_sigma2"], ROOT.RooRealVar)



def test_scale_shift(shift_scale_factory):
    scale_shift_tester(shift_scale_factory)


def test_arithmetics(arithmetics_factory):
    assert arithmetics_factory.get('mu').getVal() == 23.0


def test_legacy_syntax_factory(legacy_syntax_factory):
    scale_shift_tester(legacy_syntax_factory)


# EOF
