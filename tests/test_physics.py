#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   test_physics.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   19.04.2017
# =============================================================================
"""Test imports."""

import yaml
import yamlordereddictloader
import pytest

import ROOT

import analysis.physics as phys
import analysis.physics.factory as phys_factory
import analysis.physics.pdf_models as pdfs
from analysis.utils.logging_color import get_logger
from analysis.utils.config import ConfigError


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

    MANDATORY_PARAMETERS = ('mu',
                            'sigma1',
                            'alpha1',
                            'n1',
                            'sigma2',
                            'alpha2',
                            'n2',
                            'frac')


class ExponentialFactory(pdfs.ExponentialPdfMixin, MassFactory):
    """Exponential mass PDF.

    Parameter names:
        - 'tau'

    """

    MANDATORY_PARAMETERS = ('tau', )


class FlatQ2(phys_factory.PhysicsFactory):
    """Abstract base class for q2 PDFs.

    Implements the observable.

    """

    PARAMETERS = ('const', )

    PARAMETER_DEFAULTS = {'const': 1.0}

    def get_observables(self):
        """Get the observables for the q2 PDF.

        Returns:
            tuple[`ROOT.RooRealVar`]: q2 variable.

        """
        return (self.get("q2")
                if "q2" in self
                else self.set("q2", ROOT.RooRealVar("q2", "q2",
                                                    0.0, 19.0, "GeV^{2}/c^{4}")),)

    def get_unbound_pdf(self, name, title):
        """Get the physics PDF.

        Returns a lambda that builds the `RooPolynomial` starting from
            order 0.

        Returns:
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
                               Loader=yamlordereddictloader.Loader)
    return phys.configure_model(factory_config)


@pytest.fixture
def factory():
    """Load a PhysicsFactory."""
    return load_model("""mass:
    pdf: cb
    parameters:
        mu: L 5246.7 5200 5300
        sigma1: '@sigma/sigma/sigma/L 41 35 45'
        sigma2: '@sigma'
        n1: L 5.6689 2 9
        n2: L 1.6 0.2 2
        alpha1: L 0.25923 0.1 0.5
        alpha2: L -1.9749 -3.5 -1.0
        frac: L 0.84873 0.1 1.0""")


@pytest.fixture
def factory_with_yield():
    """Load a PhysicsFactory with yield."""
    return load_model("""mass:
    pdf: cb
    yield: L 1000 300 2000
    parameters:
        mu: L 5246.7 5200 5300
        sigma1: '@sigma/sigma/sigma/L 41 35 45'
        sigma2: '@sigma'
        n1: L 5.6689 2 9
        n2: L 1.6 0.2 2
        alpha1: L 0.25923 0.1 0.5
        alpha2: L -1.9749 -3.5 -1.0
        frac: L 0.84873 0.1 1.0""")


# pylint: disable=W0621
def test_factory_load(factory):
    """Test factory loading returns an object of the correct type."""
    return isinstance(factory, phys_factory.PhysicsFactory)


# pylint: disable=W0621
def test_factory_get_pdf(factory):
    """Test the PDF from the factory has the correct properties."""
    model = factory.get_pdf("TestFactory", "TestFactory")
    return all((isinstance(model, ROOT.RooAddPdf),
                model.GetName() == 'TestFactory',
                model.GetTitle() == 'TestFactory',
                model.createIntegral(ROOT.RooArgSet(factory.get_observables()[0])).getVal() == 173.17543630144118))


# pylint: disable=W0621
def test_factory_get_extendedpdf(factory, factory_with_yield):
    """Test the PDF from the factory has the correct properties."""
    model = factory.get_extended_pdf("TestFactory", "TestFactory", 1000)
    model_yield = factory_with_yield.get_extended_pdf("TestFactoryWithYield", "TestFactoryWithYield")
    return all((model.getVariables()["Yield"].getVal() == 1000.0,
                model_yield.getVariables()["Yield"].getVal() == 1000.0))


# pylint: disable=W0621
def test_factory_shared(factory):
    """Test that shared parameters are treated correctly."""
    model = factory.get_pdf("TestFactory", "TestFactory")
    sigma1 = model.getComponents()['TestFactoryCB1'].getVariables()['sigma']
    sigma2 = model.getComponents()['TestFactoryCB2'].getVariables()['sigma']
    return all([sigma1 == sigma2,
                sigma2.getVal() == 41.0,
                sigma2.getMin() == 35.0,
                sigma2.getMax() == 45.0])


@pytest.fixture
def prod_factory():
    """Load a ProdPhysicsFactory."""
    return load_model("""
yield: G 999 100
pdf:
    mass:
        pdf: cb
        parameters:
            mu: L 5246.7 5200 5300
            sigma1: '@sigma/sigma/sigma/L 41 35 45'
            sigma2: '@sigma'
            n1: L 5.6689 2 9
            n2: L 1.6 0.2 2
            alpha1: L 0.25923 0.1 0.5
            alpha2: L -1.9749 -3.5 -1.0
            frac: L 0.84873 0.1 1.0
    q2:
        pdf: flat
        parameters:
            const: '@sigma'
""")


# pylint: disable=W0621
def test_prodfactory_load(prod_factory):
    """Test factory loading returns an object of the correct type."""
    return all((isinstance(prod_factory, phys_factory.ProductPhysicsFactory),
                isinstance(prod_factory.get_constraints()['YieldConstraint'],
                           ROOT.RooGaussian)))


# pylint: disable=W0621
def test_prodfactory_get_pdf(prod_factory):
    """Test the PDF from the product factory has the correct properties."""
    model = prod_factory.get_pdf("TestProdFactory", "TestProdFactory")
    return all((isinstance(model, ROOT.RooProdPdf),
                model.GetName() == 'TestProdFactory',
                model.GetTitle() == 'TestProdFactory',
                model.getVariables()['mu^{mass}'].getVal() == 5246.7,  # Checks naming convention
                model.createIntegral(
                    ROOT.RooArgSet(*prod_factory.get_observables())).getVal() == 18.93855584296594,
                model.getComponents()["TestProdFactory^{q2}"].createIntegral(
                    ROOT.RooArgSet(prod_factory.get_observables()[1])).getVal() == 19.0))


# pylint: disable=W0621,C0103
def test_prodfactory_get_extendedpdf(prod_factory):
    """Test the PDF from the product factory has the correct properties."""
    model = prod_factory.get_extended_pdf("TestProdFactory", "TestProdFactory")
    return model.getVariables()["Yield"].getVal() == 999.0


# pylint: disable=W0621
def test_prodfactory_shared(prod_factory):
    """Test that shared parameters are treated correctly."""
    model = prod_factory.get_pdf("TestProdFactory", "TestProdFactory")
    model.getComponents()['TestProdFactory^{mass}CB1'].getVariables().Print("v")
    sigma1 = model.getComponents()['TestProdFactory^{mass}CB1'].getVariables()['sigma']
    sigma2 = model.getComponents()['TestProdFactory^{mass}CB2'].getVariables()['sigma']
    const = model.getComponents()['TestProdFactory^{q2}'].getVariables()['sigma']
    return all([sigma1 == sigma2,
                sigma1 == const,
                sigma2.getVal() == 41.0,
                sigma2.getMin() == 35.0,
                sigma2.getMax() == 45.0])


def test_prodfactory_error():
    """Test if a badly configured ProdFactory is picked up."""
    try:
        load_model("""
yield: G 999 100
pdf:
    mass:
        pdf: cb
        yield: G 999 100
        parameters:
            mu: L 5246.7 5200 5300
            sigma1: '@sigma/sigma/sigma/L 41 35 45'
            sigma2: '@sigma'
            n1: L 5.6689 2 9
            n2: L 1.6 0.2 2
            alpha1: L 0.25923 0.1 0.5
            alpha2: L -1.9749 -3.5 -1.0
            frac: L 0.84873 0.1 1.0
    q2:
        pdf: flat
        parameters:
            const: '@sigma'
""")
        return False
    except ConfigError:
        return True


@pytest.fixture
def sum_factory():
    """Load a SumPhysicsFactory."""
    return load_model("""
signal:
    yield: '@yield/yield/yield/G 999 100'
    pdf:
        mass:
            pdf: cb
            parameters:
                mu: L 5246.7 5200 5300
                sigma1: '@sigma/sigma/sigma/L 41 35 45'
                sigma2: '@sigma'
                n1: L 5.6689 2 9
                n2: L 1.6 0.2 2
                alpha1: L 0.25923 0.1 0.5
                alpha2: L -1.9749 -3.5 -1.0
                frac: L 0.84873 0.1 1.0
background:
    yield: '@yield'
    pdf:
        mass:
            pdf: exp
            parameters:
                tau: C -0.003
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
                mu: L 5246.7 5200 5300
                sigma1: '@sigma/sigma/sigma/L 41 35 45'
                sigma2: '@sigma'
                n1: L 5.6689 2 9
                n2: L 1.6 0.2 2
                alpha1: L 0.25923 0.1 0.5
                alpha2: L -1.9749 -3.5 -1.0
                frac: L 0.84873 0.1 1.0
background:
    pdf:
        mass:
            pdf: exp
            parameters:
                tau: C -0.003
""")


# pylint: disable=W0621
def test_sumfactory_load(sum_factory):
    """Test factory loading returns an object of the correct type."""
    return all((isinstance(sum_factory, phys_factory.SumPhysicsFactory),
                # Is the constraint loaded properly?
                isinstance(sum_factory.get_constraints()['yieldConstraint'],
                           ROOT.RooGaussian),
                # Is the constraint propagated properly?
                sum_factory.get_constraints()['yieldConstraint'] == \
                sum_factory.get_children()['background'].get_constraints()['yieldConstraint']))


# pylint: disable=W0621
def test_sumfactory_get_extendedpdf(sum_factory):
    """Test the PDF from the product factory has the correct properties."""
    model = sum_factory.get_extended_pdf("TestSumFactory", "TestSumFactory")
    return all((isinstance(model, ROOT.RooAddPdf),
                model.GetName() == 'TestSumFactory',
                model.GetTitle() == 'TestSumFactory',
                model.getVariables()["tau^{background}"].getVal() == -0.003,
                model.getVariables()["tau^{background}"].isConstant(),
                model.getComponents()["TestSumFactory^{signal}_{noext}"].createIntegral(
                    ROOT.RooArgSet(sum_factory.get_observables()[0])).getVal() == 173.17543630144118))


# pylint: disable=W0621
def test_sumfactory_shared(sum_factory):
    """Test that shared parameters are treated correctly."""
    model = sum_factory.get_pdf("TestSumFactory", "TestSumFactory")
    yield_signal = model.getComponents()['TestSumFactory^{signal}'].getVariables()['yield']
    yield_background = model.getComponents()['TestSumFactory^{background}'].getVariables()['yield']
    return all((yield_signal == yield_background,
                yield_signal.getVal() == 999))


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
                        mu: L 5246.7 5200 5300
                        sigma1: '@sigma/sigma/sigma/L 41 35 45'
                        sigma2: '@sigma'
                        n1: L 5.6689 2 9
                        n2: L 1.6 0.2 2
                        alpha1: L 0.25923 0.1 0.5
                        alpha2: L -1.9749 -3.5 -1.0
                        frac: L 0.84873 0.1 1.0
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
                        tau: C -0.003
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
                        mu: L 5246.7 5200 5300
                        sigma1: '@sigma'
                        sigma2: '@sigma'
                        n1: L 5.6689 2 9
                        n2: L 1.6 0.2 2
                        alpha1: L 0.25923 0.1 0.5
                        alpha2: L -1.9749 -3.5 -1.0
                        frac: L 0.84873 0.1 1.0
""")


# pylint: disable=W0621
def test_simfactory_load(sim_factory):
    """Test factory loading returns an object of the correct type."""
    return isinstance(sim_factory, phys_factory.SimultaneousPhysicsFactory)


# pylint: disable=W0621
def test_simfactory_get_pdf(sim_factory):
    """Test the PDF from the product factory has the correct properties."""
    model = sim_factory.get_pdf("TestSimFactory", "TestSimFactory")
    return all((isinstance(model, ROOT.RooSimultaneous),
                model.GetName() == 'TestSimFactory',
                model.GetTitle() == 'TestSimFactory',
                model.getVariables()["tau^{label1,background,mass}"].getVal() == -0.003,
                model.getVariables()["tau^{label1,background,mass}"].isConstant(),
                model.getComponents()["TestSimFactory^{label1,signal}"].createIntegral(
                    ROOT.RooArgSet(sim_factory.get_observables()[0])).getVal() == 173.17543630144118))


# pylint: disable=W0621
def test_simfactory_vs_factory(factory, sim_factory):
    """Compare that the same configuration gives the same object."""
    fac_model = factory.get_pdf("TestFactory", "TestFactory")
    sim_model = sim_factory.get_pdf("TestSimFactory", "TestSimFactory")
    return fac_model.createIntegral(
        ROOT.RooArgSet(factory.get_observables()[0])).getVal() == \
        sim_model.getComponents()["TestSimFactory^{label1,signal}"].createIntegral(
            ROOT.RooArgSet(sim_factory.get_observables()[0])).getVal()


# EOF
