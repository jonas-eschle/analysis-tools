#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   test_data.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   16.05.2017
# =============================================================================
"""Test data-related funcionality."""

import os
import tempfile
import contextlib

import pytest

import pandas as pd

from analysis.data import get_data


@pytest.fixture
def pandas_weights():
    """Dataframe containing weights."""
    return pd.DataFrame({'half': [0.5]*1000,
                         'quarter': [0.25]*1000,
                         'asym': [0.5]*500 + [0.25]*500})


@contextlib.contextmanager
def temp_file(frame):
    """Store the given frame in a temp file."""
    _, file_name = tempfile.mkstemp()
    with pd.HDFStore(file_name) as store:
        store.append('ds', frame)
    yield file_name
    os.remove(file_name)


# pylint: disable=W0621
def test_load_with_weights(pandas_weights):
    """Test loading data with weights."""
    with temp_file(pandas_weights) as file_name:
        # Let's start with a simple one
        data = get_data({'name': 'Test',
                         'source': file_name,
                         'tree': 'ds',
                         'output-format': 'root',
                         'input-type': 'pandas',
                         'weights': 'half'})
        assert data.isWeighted()
        assert data.sumEntries() == 1000.0  # Correct normalization
        data.get(0)
        assert data.weight() == 1.0  # Since all weights are equal
        # Now product of two
        data = get_data({'name': 'Test',
                         'source': file_name,
                         'tree': 'ds',
                         'output-format': 'root',
                         'input-type': 'pandas',
                         'weights': ['half', 'quarter'],
                         'weight_var': 'weight'})
        assert data.isWeighted()
        assert data.sumEntries() == 1000.0  # Correct normalization
        data.get(0)
        assert data.weight() == 1.0  # Since all weights are equal
        # This should fail
        try:
            data = get_data({'name': 'Test',
                             'source': file_name,
                             'tree': 'ds',
                             'output-format': 'root',
                             'input-type': 'pandas',
                             'weights': ['half', 'quarter']})
        except KeyError:
            pass
        else:
            assert False
        # And now product of the three to make sure it's not chance
        data = get_data({'name': 'Test',
                         'source': file_name,
                         'tree': 'ds',
                         'output-format': 'root',
                         'input-type': 'pandas',
                         'weights': ['half', 'quarter', 'asym'],
                         'weight_var': 'weight'})
        if not data.isWeighted():
            return False
        # Correct normalization
        assert data.isWeighted()
        assert data.sumEntries() == 1000.0  # Correct normalization
        data.get(0)
        assert data.weight() == 1.3333333333333333
        data.get(999)
        assert data.weight() == 0.6666666666666666


# EOF
