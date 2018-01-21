#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   test_syst.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   10.11.2017
# =============================================================================
"""Test systematics classes."""
from __future__ import print_function, division, absolute_import

from test_physics import factory, factory_with_yield
from test_physics import prod_factory
from test_physics import sum_factory, sum_factory_frac
from test_physics import sim_factory

from analysis.toys.randomizers import ToyRandomizer
from analysis.utils.root import list_to_rooargset


# pylint: disable=W0621
def test_factory_split(factory, factory_with_yield):
    """Test function splitting is done properly."""
    try:
        ToyRandomizer(factory)
    except ValueError:
        pass
    # Manual yield
    syst_fac = ToyRandomizer(factory, {'yield': 100})
    assert list(syst_fac._gen_pdfs.keys()) == [None]
    assert len(syst_fac._gen_pdfs[None]) == 1
    assert syst_fac._gen_pdfs[None][0].expectedEvents(
        list_to_rooargset(
            factory.get_observables())) == 100
    # Yield from config
    syst_fac = ToyRandomizer(factory_with_yield)
    assert list(syst_fac._gen_pdfs.keys()) == [None]
    assert len(syst_fac._gen_pdfs[None]) == 1
    assert syst_fac._gen_pdfs[None][0].expectedEvents(
        list_to_rooargset(
            factory.get_observables())) == 1000


# pylint: disable=W0621
def test_prodfactory_split(prod_factory):
    """Test function splitting is done properly."""
    syst_fac = ToyRandomizer(prod_factory)
    assert list(syst_fac._gen_pdfs.keys()) == [None]
    assert len(syst_fac._gen_pdfs[None]) == 1
    assert syst_fac._gen_pdfs[None][0].expectedEvents(
        list_to_rooargset(
            prod_factory.get_observables())) == 999


# pylint: disable=W0621
def test_sumfactory_factory_split(sum_factory, sum_factory_frac):
    """Test function splitting is done properly."""
    # With yields
    syst_fac = ToyRandomizer(sum_factory)
    assert list(syst_fac._gen_pdfs.keys()) == [None]
    assert len(syst_fac._gen_pdfs[None]) == 2
    assert syst_fac._gen_pdfs[None][0].expectedEvents(
        list_to_rooargset(
            sum_factory.get_observables())) == 999
    assert syst_fac._gen_pdfs[None][1].expectedEvents(
        list_to_rooargset(
            sum_factory.get_observables())) == 999
    # With fraction
    syst_fac = ToyRandomizer(sum_factory_frac, {'yield': 100})
    assert list(syst_fac._gen_pdfs.keys()) == [None]
    assert len(syst_fac._gen_pdfs[None]) == 1
    assert syst_fac._gen_pdfs[None][0].expectedEvents(
        list_to_rooargset(
            sum_factory.get_observables())) == 100


# pylint: disable=W0621
def test_simfactory_factory_split(sim_factory):
    """Test function splitting is done properly."""
    # With yields
    syst_fac = ToyRandomizer(sim_factory)
    assert list(syst_fac._gen_pdfs.keys()) == ['label1', 'label2']
    assert len(syst_fac._gen_pdfs['label1']) == 2
    assert syst_fac._gen_pdfs['label1'][0].expectedEvents(
        list_to_rooargset(
            sim_factory.get_observables())) == 999
    assert syst_fac._gen_pdfs['label1'][1].expectedEvents(
        list_to_rooargset(
            sim_factory.get_observables())) == 320
    assert len(syst_fac._gen_pdfs['label2']) == 1
    assert syst_fac._gen_pdfs['label2'][0].expectedEvents(
        list_to_rooargset(
            sim_factory.get_observables())) == 231

# EOF
