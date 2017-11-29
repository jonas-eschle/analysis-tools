#!/usr/bin/env python
# =============================================================================
# @file   test_config.py
# @author Jonas Eschle 'Mayou36' (jonas.eschle@cern.ch)
# @date   24.11.2017
# =============================================================================
"""Test configuration related functionality/manipulations"""
import contextlib
import tempfile
import os
import atexit

import yaml
import yamlordereddictloader
import pytest

from analysis.utils.config import load_config


def create_tempfile(suffix=None):
    """Create a temporary file and remove it on exit "guaranteed".

    Returns:
        tuple(os handle, str): Returns same objects as :py:func:`tempfile.mkstemp`.
    """

    try:
        os_handle, filename = tempfile.mkstemp(suffix=suffix)
    except Exception:  # aiming at interruptions
        print("Exception occured while creating a temp-file")
        raise
    finally:
        atexit.register(cleanup_file, filename)

    return os_handle, filename


def cleanup_file(filename):
    """Remove a file if exists."""
    try:
        os.remove(filename)
    except FileNotFoundError as error:
        pass  # file was not created at all


@contextlib.contextmanager
def temp_file():
    """Create temporary files, cleanup after exit"""
    _, file_name = create_tempfile()
    yield file_name
    os.remove(file_name)


def dump_yaml_str(config_str):
    _, filename = create_tempfile(suffix='yaml')
    with open(filename, 'w') as yaml_file:
        yaml_file.write(config_str)
    return filename


@pytest.fixture
def result_simple():
    result_str = """result:
                        bkg_pdf:
                            pdf: exp
                            parameters:
                                tau: CONST -0.003
                        signal_pdf:
                            fit-result:
                                mu: 999 99 9999
                                sigma1: '111 11 1111'
                                sigma2: '@sigma'
                                n1: 555 55 555
                                n2: 1.6 0.2 2
                                alpha1: 0.25923 0.1 0.5
                                alpha2: -1.9749 -3.5 -1.0
                                frac: 0.84873 0.1 1.0"""
    filename = dump_yaml_str(result_str)
    return filename


@pytest.fixture
def config_simple_load(result_simple):
    config_str = """
        signal:
            yield: 0.5
            pdf:
                mass:
                    pdf: cb
                    parameters:
                        load: {yaml_res}:result/signal_pdf/fit-result
                        modify: 
                            mu: 5246.7 5200 5300
                            sigma1: '@sigma/sigma/sigma/41 35 45'
                            n1: 5.6689 2 9
        background:
            pdf:
                mass:
                    load: {yaml_res}:result/bkg_pdf""".format(yaml_res=result_simple)  # tempfile name
    filename = dump_yaml_str(config_str)

    return filename


@pytest.fixture
def config_simple_load_target():
    """What we want config_simple_load to look like"""
    loaded_config = yaml.load("""
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
        """,
                              Loader=yamlordereddictloader.Loader)
    return loaded_config


def test_simple(config_simple_load, config_simple_load_target):
    config = load_config(config_simple_load)
    assert config == config_simple_load_target
