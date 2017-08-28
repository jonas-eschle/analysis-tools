#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   model_efficiency.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   07.04.2017
# =============================================================================
"""Script to model the efficiency from an input dataset."""

import os
import argparse

import matplotlib.pyplot as plt

from analysis import get_global_var
from analysis.data import get_data
from analysis.utils.logging_color import get_logger
import analysis.utils.config as _config
import analysis.utils.paths as _paths

from analysis.efficiency import get_efficiency_model_class, load_efficiency_model


logger = get_logger('analysis.efficiency.calculate_efficiency')
# Register plot path
get_efficiency_plot_path = _paths.register_path('efficiency_plot',
                                                ['data_files', 'efficiency'],
                                                'eps',
                                                lambda name, args, kwargs: name + '_%s' % kwargs['var'])


def run(config_files, link_from):
    """Run the script.

    If the efficiency file exists, only the plots are remade.

    Arguments:
        config_files (list[str]): Path to the configuration files.
        link_from (str): Path to link the results from.

    Raises:
        OSError: If there either the configuration file does not exist some
            of the input files cannot be found.
        KeyError: If some configuration data are missing.
        ValueError: If there is any problem in configuring the efficiency model.
        RuntimeError: If there is a problem during the efficiency fitting.

    """
    try:
        config = _config.load_config(*config_files,
                                     validate=['name',
                                               'data/source',
                                               'data/tree',
                                               'parameters',
                                               'model',
                                               'variables'])
    except OSError:
        raise OSError("Cannot load configuration files: %s",
                      config_files)
    except _config.ConfigError as error:
        if 'name' in error.missing_keys:
            logger.error("No name was specified in the config file!")
        if 'data/file' in error.missing_keys:
            logger.error("No input data specified in the config file!")
        if 'data/tree' in error.missing_keys:
            logger.error("No input data specified in the config file!")
        if 'model' in error.missing_keys:
            logger.error("No efficiency model specified in the config file!")
        if 'parameters' in error.missing_keys:
            logger.error("No efficiency model parameters specified in the config file!")
        if 'variables' in error.missing_keys:
            logger.error("No efficiency variables to model have been specified in the config file!")
        raise KeyError("ConfigError raised -> %s" % error.missing_keys)
    except KeyError as error:
        logger.error("YAML parsing error -> %s", error)
    # Do checks and load things
    plot_files = {}
    if config.get('plot', False):
        for var_name in config['variables']:
            plot_files[var_name] = get_efficiency_plot_path(config['name'],
                                                            var=var_name)
    efficiency_class = get_efficiency_model_class(config['model'])
    if not efficiency_class:
        raise ValueError("Unknown efficiency model -> %s", config['model'])
    # Let's do it
    # pylint: disable=E1101
    if not all(os.path.exists(file_name)
               for file_name in plot_files.values()) or \
            not os.path.exists(_paths.get_efficiency_path(config['name'])):  # If plots don't exist, we load data
        logger.info("Loading data, this may take a while...")
        weight_var = config['data'].get('weight-var-name', None)
        # Prepare data
        config['data']['output-format'] = 'pandas'
        config['data']['variables'] = list(config['variables'])
        if weight_var:
            config['data']['variables'].append(weight_var)
        input_data = get_data(config['data'], **{'output-format': 'pandas'})
        if weight_var:
            logger.info("Data loaded, using %s as weight", weight_var)
        else:
            logger.info("Data loaded, not using any weights")

        if not os.path.exists(_paths.get_efficiency_path(config['name'])):
            logger.info("Fitting efficiency model")
            try:
                eff = efficiency_class.fit(input_data, config['variables'], weight_var, **config['parameters'])
            except (ValueError, TypeError) as error:
                raise ValueError("Cannot configure the efficiency model -> %s", error.message)
            except KeyError as error:
                raise RuntimeError("Missing key -> %s", error)
            except Exception as error:
                raise RuntimeError(error)
            output_file = eff.write_to_disk(config['name'], link_from)
            logger.info("Written efficiency file -> %s", output_file)
        else:
            logger.warning("Output efficiency already exists, only redoing plots")
            eff = load_efficiency_model(config['name'])
        if plot_files:
            import seaborn as sns
            sns.set_style("white")
            plt.style.use('file://%s' % os.path.join(get_global_var('STYLE_PATH'),
                                                     'matplotlib_LHCb.mplstyle'))
            plots = eff.plot(input_data, weight_var, labels=config.get('plot-labels', {}))
            for var_name, plot in plots.items():
                logger.info("Plotting '%s' efficiency -> %s",
                            var_name, plot_files[var_name])
                plot.savefig(plot_files[var_name], bbox_inches='tight')
    else:
        logger.info("Efficiency file exists: %s. Nothing to do!",
                    _paths.get_efficiency_path(config['name']))


def main():
    """Efficiency modeling application.

    Parses the command line and fits the efficiency, catching intermediate
    errors and transforming them to status codes.

    Status codes:
        0: All good.
        1: Error in the configuration files.
        2: Files missing (configuration or input data).
        3: Error configuring efficiency model.
        4: Error in the efficiency modeling process. An exception is logged.
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
        get_logger('analysis.efficiency').setLevel(10)
    try:
        exit_status = 0
        run(args.config, args.link_from)
    except KeyError:
        exit_status = 1
        logger.exception("Bad configuration given")
    except OSError, error:
        exit_status = 2
        logger.error(str(error))
    except ValueError:
        exit_status = 3
        logger.exception("Problem configuring efficiency model")
    except RuntimeError as error:
        exit_status = 4
        logger.exception("Error in fitting model")
    # pylint: disable=W0703
    except Exception as error:
        exit_status = 128
        logger.exception('Uncaught exception -> %s', repr(error))
    finally:
        parser.exit(exit_status)


if __name__ == "__main__":
    main()

# EOF
