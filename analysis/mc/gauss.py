#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   gauss.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   18.11.2017
# =============================================================================
"""Gauss options.

Extracted from the LHCb Step Manager.

"""
from __future__ import print_function, division, absolute_import

# pylint: disable=C0330
GAUSS_CONFIG = {# Step name: Sim09c - 2011 - MU - Pythia8
                ('sim09c', 2011, 'up'): {'version': 'v49r8',
                                         'options': ['$APPCONFIGOPTS/Gauss/Sim08-Beam3500GeV-mu100-2011-nu2.py',
                                                     '$APPCONFIGOPTS/Gauss/DataType-2011.py',
                                                     '$APPCONFIGOPTS/Gauss/RICHRandomHits.py',
                                                     '$APPCONFIGOPTS/Gauss/NoPacking.py',
                                                     '$LBPYTHIA8ROOT/options/Pythia8.py',
                                                     '$APPCONFIGOPTS/Gauss/G4PL_FTFP_BERT_EmNoCuts.py'],
                                         'dddb': 'dddb-20170721-1',
                                         'conddb': 'sim-20160614-1-vc-mu100'},
                # Step name: Sim09c - 2011 - MD - Pythia8
                ('sim09c', 2011, 'down'): {'version': 'v49r8',
                                           'options': ['$APPCONFIGOPTS/Gauss/Sim08-Beam3500GeV-md100-2011-nu2.py',
                                                       '$APPCONFIGOPTS/Gauss/DataType-2011.py',
                                                       '$APPCONFIGOPTS/Gauss/RICHRandomHits.py',
                                                       '$APPCONFIGOPTS/Gauss/NoPacking.py',
                                                       '$LBPYTHIA8ROOT/options/Pythia8.py',
                                                       '$APPCONFIGOPTS/Gauss/G4PL_FTFP_BERT_EmNoCuts.py'],
                                           'dddb': 'dddb-20170721-1',
                                           'conddb': 'sim-20160614-1-vc-md100'},
                # Step name: Sim09c - 2012 - MU - Pythia8
                ('sim09c', 2012, 'up'): {'version': 'v49r8',
                                         'options': ['$APPCONFIGOPTS/Gauss/Sim08-Beam4000GeV-mu100-2012-nu2.5.py',
                                                     '$APPCONFIGOPTS/Gauss/DataType-2012.py',
                                                     '$APPCONFIGOPTS/Gauss/RICHRandomHits.py',
                                                     '$APPCONFIGOPTS/Gauss/NoPacking.py',
                                                     '$LBPYTHIA8ROOT/options/Pythia8.py',
                                                     '$APPCONFIGOPTS/Gauss/G4PL_FTFP_BERT_EmNoCuts.py'],
                                         'dddb': 'dddb-20170721-2',
                                         'conddb': 'sim-20160321-2-vc-mu100'},
                # Step name: Sim09c - 2012 - MD - Pythia8
                ('sim09c', 2012, 'down'): {'version': 'v49r8',
                                           'options': ['$APPCONFIGOPTS/Gauss/Sim08-Beam4000GeV-md100-2012-nu2.5.py',
                                                       '$APPCONFIGOPTS/Gauss/DataType-2012.py',
                                                       '$APPCONFIGOPTS/Gauss/RICHRandomHits.py',
                                                       '$APPCONFIGOPTS/Gauss/NoPacking.py',
                                                       '$LBPYTHIA8ROOT/options/Pythia8.py',
                                                       '$APPCONFIGOPTS/Gauss/G4PL_FTFP_BERT_EmNoCuts.py'],
                                           'dddb': 'dddb-20170721-2',
                                           'conddb': 'sim-20160321-2-vc-md100'},
                # Step name: Sim09c - 2015 Nominal - MU - Nu1.6 (Lumi 4 at 25ns) - 25ns spillover - Pythia8
                ('sim09c', 2015, 'up'): {'version': 'v49r8',
                                         'options': ['$APPCONFIGOPTS/Gauss/Beam6500GeV-mu100-2015-nu1.6.py',
                                                     '$APPCONFIGOPTS/Gauss/EnableSpillover-25ns.py',
                                                     '$APPCONFIGOPTS/Gauss/DataType-2015.py',
                                                     '$APPCONFIGOPTS/Gauss/RICHRandomHits.py',
                                                     '$APPCONFIGOPTS/Gauss/NoPacking.py',
                                                     '$LBPYTHIA8ROOT/options/Pythia8.py',
                                                     '$APPCONFIGOPTS/Gauss/G4PL_FTFP_BERT_EmNoCuts.py'],
                                         'dddb': 'dddb-20170721-3',
                                         'conddb': 'sim-20161124-vc-mu100'},
                # Step name: Sim09c - 2015 Nominal - MD - Nu1.6 (Lumi 4 at 25ns) - 25ns spillover - Pythia8
                ('sim09c', 2015, 'down'): {'version': 'v49r8',
                                           'options': ['$APPCONFIGOPTS/Gauss/Beam6500GeV-md100-2015-nu1.6.py',
                                                       '$APPCONFIGOPTS/Gauss/EnableSpillover-25ns.py',
                                                       '$APPCONFIGOPTS/Gauss/DataType-2015.py',
                                                       '$APPCONFIGOPTS/Gauss/RICHRandomHits.py',
                                                       '$APPCONFIGOPTS/Gauss/NoPacking.py',
                                                       '$LBPYTHIA8ROOT/options/Pythia8.py',
                                                       '$APPCONFIGOPTS/Gauss/G4PL_FTFP_BERT_EmNoCuts.py'],
                                           'dddb': 'dddb-20170721-3',
                                           'conddb': 'sim-20161124-vc-md100'},
                # Step name: Sim09c - 2016 - MU - Nu1.6 (Lumi 4 at 25ns) - 25ns spillover - Pythia8
                ('sim09c', 2016, 'up'): {'version': 'v49r8',
                                         'options': ['$APPCONFIGOPTS/Gauss/Beam6500GeV-mu100-2016-nu1.6.py',
                                                     '$APPCONFIGOPTS/Gauss/EnableSpillover-25ns.py',
                                                     '$APPCONFIGOPTS/Gauss/DataType-2016.py',
                                                     '$APPCONFIGOPTS/Gauss/RICHRandomHits.py',
                                                     '$APPCONFIGOPTS/Gauss/NoPacking.py',
                                                     '$LBPYTHIA8ROOT/options/Pythia8.py',
                                                     '$APPCONFIGOPTS/Gauss/G4PL_FTFP_BERT_EmNoCuts.py'],
                                         'dddb': 'dddb-20170721-3',
                                         'conddb': 'sim-20170721-2-vc-mu100'},
                # Step name: Sim09c - 2016 - MD - Nu1.6 (Lumi 4 at 25ns) - 25ns spillover - Pythia8
                ('sim09c', 2016, 'down'): {'version': 'v49r8',
                                           'options': ['$APPCONFIGOPTS/Gauss/Beam6500GeV-md100-2016-nu1.6.py',
                                                       '$APPCONFIGOPTS/Gauss/EnableSpillover-25ns.py',
                                                       '$APPCONFIGOPTS/Gauss/DataType-2016.py',
                                                       '$APPCONFIGOPTS/Gauss/RICHRandomHits.py',
                                                       '$APPCONFIGOPTS/Gauss/NoPacking.py',
                                                       '$LBPYTHIA8ROOT/options/Pythia8.py',
                                                       '$APPCONFIGOPTS/Gauss/G4PL_FTFP_BERT_EmNoCuts.py'],
                                           'dddb': 'dddb-20170721-3',
                                           'conddb': 'sim-20170721-2-vc-md100'}}


def get_gauss_version(sim_version, year):
    """Get the Gauss version for a given simulation configuration.

    Arguments:
        sim_version (str): Simulation version.
        year (int): Year to generate.

    Return:
        str: Gauss version.

    Raise:
        KeyError: If there is no configuration registered with the given input parameters.
        AssertionError: If the saved configurations are not coherent.

    """
    year = int(year)
    sim_version = sim_version.lower()
    versions = set(info['version']
                   for (sim, conf_year, mag), info in GAUSS_CONFIG.items()
                   if sim == sim_version and conf_year == year)
    if not versions:
        raise KeyError("Unknown Gauss configuration: {}, {}".format(sim_version, year))
    assert len(versions) == 1
    return versions.pop()


def get_gaudirun_options(sim_version, year, magnet_polarity, simulate_detector=False):
    """Get the options for gaudirun.py.

    Arguments:
        sim_version (str): Simulation version.
        year (int): Year to generate.
        magnet_polarity (str): Magnet polarity to generate.
        simulate_detector (bool, optional): Simulate detector interaction or just keep
            the Pythia output. Defaults to False.

    Return:
        list: Options to run gaudirun.py.

    Raise:
        KeyError: If there is no configuration registered with the given input parameters.

    """
    key = (sim_version.lower(), int(year), magnet_polarity.lower().lstrip('mag').lstrip('magnet'))
    if key not in GAUSS_CONFIG:
        raise KeyError("Unknown Gauss configuration: {}, {}, {}".format(sim_version, year, magnet_polarity))
    options = GAUSS_CONFIG[key]['options']
    if simulate_detector:
        options.append('$GAUSSOPTS/GenStandAlone.py')
    return options


def get_db_tags(sim_version, year, magnet_polarity):
    """Get the database tags for the given simulation configuration.

    Arguments:
        sim_version (str): Simulation version.
        year (int): Year to generate.
        magnet_polarity (str): Magnet polarity to generate.

    Return:
        tuple: DDDB tag and CondDB tag.

    Raise:
        KeyError: If there is no configuration registered with the given input parameters.

    """
    key = (sim_version.lower(), int(year), magnet_polarity.lower().lstrip('mag').lstrip('magnet'))
    if key not in GAUSS_CONFIG:
        raise KeyError("Unknown Gauss configuration: {}, {}, {}".format(sim_version, year, magnet_polarity))
    return GAUSS_CONFIG[key]['dddb'], GAUSS_CONFIG[key]['conddb']


# EOF
