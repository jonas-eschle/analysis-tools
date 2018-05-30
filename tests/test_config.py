#!/usr/bin/env python
# =============================================================================
# @file   test_config.py
# @author Jonas Eschle 'Mayou36' (jonas.eschle@cern.ch)
# @date   24.11.2017
# =============================================================================
"""Test configuration related functionality/manipulations"""
from __future__ import print_function, division, absolute_import

import contextlib
import tempfile
import os
import atexit
import sys

import yaml
import yamlloader
import pytest

from analysis.utils.config import load_config, ConfigError

if sys.version_info[0] < 3:
    FileNotFoundError = OSError  # PY2 "backport"


def create_tempfile(suffix=None):
    """Create a temporary file and remove it on exit "guaranteed".

    Returns:
        tuple(os handle, str): Returns same objects as :py:func:`tempfile.mkstemp`.
    """

    try:
        os_handle, filename = tempfile.mkstemp(suffix=suffix)
    except Exception:  # aiming at interruptions
        print("Exception occurred while creating a temp-file")
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
                            yield: 0.9
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
def result_simple_signal():
    result_str = """
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
        """
    filename = dump_yaml_str(result_str)
    return filename


@pytest.fixture
def config_simple_load(result_simple):
    config_str = """
        globals:
            glob_var1: CONST 5
            glob_dict2:
                glob_var21: CONST 21
                glob_var22: VAR 4.0 2.2 5.6
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
                    load: {yaml_res}:result/bkg_pdf""".format(
        yaml_res=result_simple)  # tempfile name
    filename = dump_yaml_str(config_str)

    return filename


@pytest.fixture
def config_simple_load_signal(result_simple_signal):
    config_str = """
        signal:
            load: {yaml_res}:signal
            modify: 
                yield: 0.5
                pdf:
                    mass:
                        parameters: 
                            mu: 5246.7 5200 5300
                            sigma1: '@sigma/sigma/sigma/41 35 45'
                            n1: 5.6689 2 9
        background:
            pdf:
                load: {yaml_res}:background/pdf""".format(
        yaml_res=result_simple_signal)  # tempfile name
    filename = dump_yaml_str(config_str)

    return filename


@pytest.fixture
def config_simple_fail_noload(result_simple):
    config_str = """
        signal:
            yield: 0.5
            pdf:
                mass:
                    pdf: cb
                    parameters:
                        load: {yaml_res}:result/signal_pdf/fit-result 
                        mu: 5246.7 5200 5300
        background:
            pdf:
                mass:
                    load: {yaml_res}:result/bkg_pdf""".format(
        yaml_res=result_simple)  # tempfile name
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
                              Loader=yamlloader.ordereddict.CLoader)
    return loaded_config


def test_simple(config_simple_load, config_simple_load_target):
    config = load_config(config_simple_load)
    assert config == config_simple_load_target


def test_simple_signal(config_simple_load_signal, config_simple_load_target):
    config = load_config(config_simple_load_signal)
    assert config == config_simple_load_target


def test_fails_loudly(config_simple_fail_noload):
    with pytest.raises(ConfigError) as error_info:
        load_config(config_simple_fail_noload)


# test globals replacement

@pytest.fixture
def config_simple_globals_1():
    """Config with globals"""
    config_str = """
        globals:
            glob_mass_exp: 
                pdf: exp
                parameters:
                    tau: CONST -0.003
        signal:
            yield: 0.5
            pdf:
                mass:
                    pdf: cb
                    parameters:
                        mu: 5246.7 5200 5300
                        sigma1: globals.glob_sigma1
                        sigma2: '@sigma'
                        n1: globals.glob_n1
                        n2: 1.6 0.2 2
                        alpha1: globals.glob_alpha.alpha1
                        alpha2: -1.9749 -3.5 -1.0
                        frac: 0.84873 0.1 1.0
        background1:
            pdf:
                mass: globals.glob_mass_exp
        """
    filename = dump_yaml_str(config_str)

    return filename


@pytest.fixture
def config_simple_globals_2():
    """Config with globals"""
    config_str = """
        globals:
            glob_sigma1: '@sigma/sigma/sigma/41 35 45'
            glob_alpha:
                alpha1: 0.25923 0.1 0.5
            glob_n1: 5.6689 2 9
        background2:
            pdf:
                mass: globals.glob_mass_exp
                    
        """
    filename = dump_yaml_str(config_str)

    return filename


@pytest.fixture
def config_simple_globals_target():
    """What we want config_simple_globals_{1, 2} to look like"""
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
        background1:
            pdf:
                mass:
                    pdf: exp
                    parameters:
                        tau: CONST -0.003
        background2:
            pdf:
                mass:
                    pdf: exp
                    parameters:
                        tau: CONST -0.003
        """,
                              Loader=yamlloader.ordereddict.CLoader)
    return loaded_config


def test_global_replace(config_simple_globals_1, config_simple_globals_2,
                        config_simple_globals_target):
    config = load_config(config_simple_globals_1, config_simple_globals_2)
    assert config == config_simple_globals_target
