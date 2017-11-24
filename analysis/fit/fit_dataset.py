#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   fit_dataset.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   07.04.2017
# =============================================================================
"""Fit a dataset using one of the registered strategies."""

import os
import argparse

import ROOT

import analysis.utils.config as _config
from analysis.physics import configure_model
from analysis.fit import fit
from analysis.fit.result import FitResult
from analysis.data import get_data
from analysis.data.writers import write_dataset
from analysis.utils.logging_color import get_logger
from analysis.utils.root import list_to_rooarglist
from analysis.utils.paths import prepare_path, get_splot_path

logger = get_logger('analysis.fit.fit_dataset')


def run(config_files, link_from, verbose):
    """Run the script.

    Loads the data and fits it according to the configuration.

    Arguments:
        config_files (list[str]): Path to the configuration files.
        link_from (str): Path to link the results from.
        verbose (bool): Give verbose output?

    Raise:
        OSError: If there either the configuration file does not exist some
            of the input data cannot be found, or if the output sPlot exists.
        KeyError: If some configuration data are missing or wrong.
        ValueError: If there is any problem in configuring the PDF factories.
        AttributeError: If there is any problem loading the data.
        RuntimeError: If there is a problem during the fitting.

    """
    def find_yield(factory, name):
        """Find the yield variable of the given PDF.

        Arguments:
            factory (analysis.physics.PhysicsFactory): Factory to scan.
            name (str): Name of the PDF.

        Return:
            RooRealVar

        Raise:
            KeyError: When the PDF cannot be found.

        """
        children = factory.get_children()
        if name in children:
            return children[name].get_yield_var()
        else:
            for child in children.values():
                yield_ = find_yield(child, name)
                if yield_:
                    return yield_
        return None

    try:
        config = _config.load_config(*config_files,
                                     validate=['name',
                                               'data',
                                               'model'])
    except OSError:
        raise OSError("Cannot load configuration files: {}".format(config_files))
    except _config.ConfigError as error:
        if 'name' in error.missing_keys:
            logger.error("No name was specified in the config file!")
        if 'data' in error.missing_keys:
            logger.error("No input data specified in the config file!")
        if 'model' in error.missing_keys:
            logger.error("No fit model specified in the config file!")
        raise KeyError("ConfigError raised -> {}".format(', '.join(error.missing_keys)))
    except KeyError as error:
        logger.error("YAML parsing error -> %s", error)
    save_fit = config.get('fit', {}).pop('save', False)
    # Get the PDF
    try:
        logger.debug("Loading physics model")
        factory = configure_model(config['model'])
    except KeyError:
        raise ValueError("Error loading model")
    # Get the data
    try:
        logger.debug("Loading data to fit")
        data = get_data(config['data'])
    except (AttributeError, KeyError, ValueError) as error:
        logger.error(str(error))
        raise AttributeError("Error loading data")
    except OSError:
        raise OSError("Cannot find input data")
    # Fit
    try:
        logger.debug("Fitting dataset")
        result = fit(factory,
                     "FitPDF",
                     config.get('fit', {}).pop('strategy', 'simple'),
                     data,
                     Extended=factory.is_extended(),
                     verbose=verbose,
                     **config.get('fit', {}))
    except ValueError:
        logger.exception("Fitting error")
        raise RuntimeError()
    if save_fit:
        logger.debug("Saving FitResult")
        FitResult.from_roofit(result).to_yaml_file(config['name'])
    splot_config = bool(config.get('splot', None))
    if splot_config:
        # Checks
        for key in ('components-to-splot', 'output-file'):
            if key not in splot_config:
                raise KeyError("Missing sPlot configuration -> '{}'".format(key))
        if not factory.is_extended():
            raise KeyError("Cannot do sPlot on a non-extended PDF")
        # Get components
        pdf = factory.get_extended_pdf("FitPDF", "FitPDF")
        components = splot_config['components-to-splot']
        yields = [find_yield(factory, component) for component in components]
        logger.debug("Found yields -> %s", ", ".join(yield_.GetName() for yield_ in yields))
        # Calculate sPlot
        yields = list_to_rooarglist(yields)
        logger.debug("Calculating sPlot")
        splot = ROOT.RooStats.SPlot('sPlot', 'sPlot', data, pdf, yields)
        # Save
        splot_file = splot_config['output-file']
        if not os.path.splitext(splot_file)[1]:
            logger.error("Output sPlot file needs to be given an extension")
            raise KeyError("Undefined extension for sPlot output file")
        if not os.path.isabs(splot_file):  # It's just a name, use get_splot_path
            _, splot_file_src, splot_file_dest = prepare_path(splot_file,
                                                              path_func=get_splot_path,
                                                              link_from=link_from)
        else:
            splot_file_src = splot_file_dest = splot_file
        logger.debug("Writing out sPlotted dataset -> %s", splot_file)
        if splot_config.get('overwrite', False) and os.path.exists(splot_file):
            logger.debug("Removing old sPlot file")
            os.remove(splot_file)
        try:
            write_dataset(splot_file_src, splot)
        except OSError:
            logger.error("Cannot write sPlot, file exists -> %s", config['splot']['output-file'])
            raise
        if splot_file_src != splot_file_dest:
            if os.path.exists(splot_file_dest):
                logger.warning("Stray symlink present. Removing -> %s", splot_file_dest)
                os.path.remove(splot_file_dest)
            os.symlink(splot_file_src, splot_file_dest)


def main():
    """Dataset fitting application.

    Parses the command line and fits the data, catching intermediate
    errors and transforming them to status codes.

    Status codes:
        0: All good.
        1: Error in the configuration files.
        2: Files missing (configuration or data).
        3: Error configuring physics factories.
        4: Error in loading data.
        5: Error in fitting.
        128: Uncaught error. An exception is logged.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Verbose output")
    parser.add_argument('--link-from',
                        action='store', type=str, default='',
                        help="Folder to actually store the fit results")
    parser.add_argument('config',
                        action='store', type=str, nargs='+',
                        help="Configuration files")
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(1)
    else:
        ROOT.RooMsgService.instance().setGlobalKillBelow(ROOT.RooFit.WARNING)
    try:
        exit_status = 0
        run(args.config, args.link_from, args.verbose)
    except KeyError:
        exit_status = 1
        logger.exception("Bad configuration given")
    except OSError, error:
        exit_status = 2
        logger.error(str(error))
    except ValueError:
        exit_status = 3
        logger.error("Problem configuring physics factories")
    except AttributeError:
        exit_status = 4
        logger.exception("Error loading data")
    except RuntimeError:
        exit_status = 5
        logger.error("Error in fitting data")
    # pylint: disable=W0703
    except Exception as error:
        exit_status = 128
        logger.exception('Uncaught exception -> %s', repr(error))
    finally:
        parser.exit(exit_status)


if __name__ == "__main__":
    main()

# EOF
