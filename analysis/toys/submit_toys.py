#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   submit_toys.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   13.03.2017
# =============================================================================
"""Submission of toys to the cluster.

This submission is forced to happen through a config file in YAML format
to ensure reproducibility.

Mandatory configuration keys are:
    - name: Name of the job

Then, according to the type of job, there's a few extra mandatory keys:
    - Fitting toys:
        + fit/nfits: Total number of fits to perform.
        + fit/nfits-per-job: Number of fits produced per job.
    - Generation toys:
        + gen/nevents: Total number of events to produce.
        + gen/nevents-per-job: Number of events produced per job.

Optional configuration keys:
    - batch/runtime: In the HH:MM:SS format. Defaults to 08:00:00.

"""
from __future__ import print_function, division, absolute_import

import argparse
import os
import itertools
import tempfile

from analysis import get_global_var
import analysis.utils.paths as _paths
import analysis.utils.config as _config
from analysis.utils.logging_color import get_logger
from analysis.toys.submitter import ToySubmitter

logger = get_logger('analysis.toys.submit')


# Submitter classes
# pylint: disable=too-few-public-methods
class FitSubmitter(ToySubmitter):
    """Specialization of ToySubmitter to submit the fitting of toys."""

    VALIDATION = {'name': "No name was specified in the config file!",
                  'fit/nfits': "Number of fits not specified!",
                  # 'fit/nfits-per-job': "Number of fits per job not specified!",
                  # 'fit-model': "No pdfs were specified in the config file!",
                  'data': "No input data was specified in the config file!"}
    # pylint: disable=E1101
    TOY_PATH_GETTER = staticmethod(_paths.get_toy_fit_path)
    TOY_CONFIG_PATH_GETTER = staticmethod(_paths.get_toy_fit_config_path)
    ALLOWED_CONFIG_DIFFS = ['gen/nevents',
                            'gen/nevents-per-job',
                            'batch/runtime']
    NTOYS_KEY = 'fit/nfits'
    NTOYS_PER_JOB_KEY = 'fit/nfits-per-job'


# pylint: disable=too-few-public-methods
class GenerationSubmitter(ToySubmitter):
    """Specialization of ToySubmitter to submit generation of toys."""

    VALIDATION = {'name': "No name was specified in the config file!",
                  'gen/nevents': "Number of events not specified!",
                  # 'gen/nevents-per-job': "Number of events per job not specified!",
                  'gen-model': "No pdfs were specified in the config file!"}
    # pylint: disable=E1101
    TOY_PATH_GETTER = staticmethod(_paths.get_toy_path)
    TOY_CONFIG_PATH_GETTER = staticmethod(_paths.get_toy_config_path)
    ALLOWED_CONFIG_DIFFS = ['gen/nevents',
                            'gen/nevents-per-job',
                            'batch/runtime']
    NTOYS_KEY = 'gen/nevents'
    NTOYS_PER_JOB_KEY = 'gen/nevents-per-job'


TOY_TYPES = {'gen': (GenerationSubmitter, 'generate_toys.py'),
             'fit': (FitSubmitter, 'fit_toys.py')}


# Scan function
def process_scan_val(value, other_values=None):
    """Process the string of a scan specification.

    Several structures are allowed:
        - `VALUES X ...`: Explicitly give values. Every value that follows the `V` is
        taken.
        - `RANGE Min Max Step`: Range. Values can be floats, unlike python's `range`.
        - `INTERPOLATE value`: Use the value of other variables to interpolate the list.
        For example:
            ```
            sigma: VALUES 1 2 3
            sigmafile: INTERPOLATE file_{sigma}
            ```

        would generate the list `[file_1, file_2 file_3]` for `sigmafile`. The only limitation
        of this interpolation is that the interpolating variable needs to be defined before the
        interpolation.

        - `SCALE var value` can be used to perform an interpolation with a product. For example:
            ```
            sigma: VALUES 1 2 3
            sigma_bkg: SCALE sigma 2
            ```

        would generate the values `[2, 4, 6]` for `sigma_bkg`. The only limitation of this
        interpolation is that the interpolating variable needs to be defined before the
        interpolation.


    Arguments:
        value (str): String specification of the value to scan.
        other_values (dict, optional): Values to use for interpolation.

    Raise:
        ValueError: When the scan specification is not properly formed.

    """
    split_value = value.split()
    action = split_value[0].lower()
    if action == 'values':  # Values
        values = split_value[1:]
    elif action == 'range':  # Range
        try:
            min_, max_, step = split_value[1:]
        except ValueError:
            raise ValueError('Badly specified range')
        try:
            # pylint: disable=W0106
            [int(val) for val in (min_, max_, step)]
            num_func = int
        except ValueError:
            num_func = float
        min_, max_, step = [num_func(val) for val in (min_, max_, step)]
        values = []
        curr_val = min_
        while True:
            if curr_val >= max_:
                break
            values.append(curr_val)
            curr_val += step
    elif action == 'interpolate':
        if not other_values:
            raise ValueError('No values to interpolate')
        val_to_format = ' '.join(split_value[1:])
        values = [val_to_format.format(**{key: vals[val_num]
                                          for key, vals in other_values.items()})
                  for val_num in range(len(list(other_values.values())[0]))]
        try:
            values = [int(val) for val in values]
        except ValueError:
            try:
                values = [float(val) for val in values]
            except ValueError:
                pass
    elif action == 'scale':
        if not other_values:
            raise ValueError('No values to interpolate')
        try:
            var_name, scale_factor = split_value[1:]
        except ValueError:
            raise ValueError("Badly specified scale")
        if var_name not in other_values:
            raise ValueError("Unknown variable -> {}".format(var_name))
        values = [var_val * float(scale_factor)
                  for var_val in other_values[var_name]]
    else:
        raise ValueError('Unknown scan command -> {}'.format(action))
    return values


# Submit!
def main():
    """Toy fitting submission application.

    Parses the command line, configures the toy fitters and submit the
    jobs, catching intermediate errors and transforming them to status codes.

    Status codes:
        0: All good.
        1: Error in the configuration files.
        2: Error in preparing the output folders.
        3: Conflicting options given.
        4: A non-matching configuration file was found in the output.
        5: The queue submission command cannot be found.
        128: Uncaught error. An exception is logged.

    """

    def flatten(list_, typ_):
        """Flatten a list."""
        return list(sum(list_, typ_))

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Verbose output")
    parser.add_argument('--link-from',
                        action='store', type=str,
                        help="Folder to actually store the toy files")
    parser.add_argument('--extend',
                        action='store_true', default=False,
                        help="Extend previous production")
    parser.add_argument('--overwrite',
                        action='store_true', default=False,
                        help="Overwrite previous production")
    parser.add_argument('config',
                        action='store', type=str, nargs='+',
                        help="Configuration file")
    args = parser.parse_args()
    if args.verbose:
        get_logger('analysis').setLevel(1)
        logger.setLevel(1)
    try:
        config = _config.load_config(*args.config)
        # Which type of toy are we running?
        script_to_run = None
        submitter = None
        for toy_type, (toy_class, script_name) in TOY_TYPES.items():
            if toy_type in config:
                script_to_run = script_name
                submitter = toy_class
        if submitter is None:
            raise KeyError("Unknown job type")
        # Is there something to scan?
        scan_config = 'scan' in config
        if scan_config:
            config_files = []
            base_config = _config.unfold_config(config)
            scan_groups = []
            for scan_group in config['scan']:
                scan_group_dict = {}
                for key, val_str in scan_group.items():
                    scan_group_dict[key] = process_scan_val(val_str, scan_group_dict)
                scan_groups.append(scan_group_dict)
            # Check lengths
            if not all(len({len(val) for val in scan_group.values()}) == 1
                       for scan_group in scan_groups):
                raise ValueError("Unmatched length in scan parameters")
            # Build values to scan
            keys, values = list(zip(*[zip(*scan_group.items()) for scan_group in scan_groups]))
            keys = flatten(keys, tuple())
            for value_tuple in itertools.product(*[zip(*val) for val in values]):
                values = dict(zip(keys, flatten(value_tuple, tuple())))
                temp_config = dict(base_config)
                del temp_config['scan']
                temp_config['name'] = temp_config['name'].format(**values)
                for key, value in values.items():
                    temp_config[key] = value
                logger.debug("Creating configuration %s for scan values -> %s",
                             temp_config['name'],
                             ", ".join('{}: {}'.format(*val) for val in values.items()))
                # Write temp_file
                with tempfile.NamedTemporaryFile(delete=False) as file_:
                    file_name = file_.name
                _config.write_config(_config.fold_config(list(temp_config.items())), file_name)
                config_files.append(file_name)
        else:
            config_files = args.config
    # pylint: disable=W0702
    except:
        logger.exception("Bad configuration given")
        parser.exit(1)
    try:
        script_to_run = os.path.join(get_global_var('BASE_PATH'),
                                     'toys',
                                     script_to_run)
        for config_file in config_files:
            submitter(config_files=[config_file],
                      link_from=args.link_from,
                      extend=args.extend,
                      overwrite=args.overwrite,
                      verbose=args.verbose).run(script_to_run,)
            if scan_config:
                os.remove(config_file)
        exit_status = 0
    except KeyError:
        logger.error("Bad configuration given")
        exit_status = 1
    except OSError as error:
        logger.error(str(error))
        exit_status = 2
    except ValueError:
        logger.error("Conflicting options found")
        exit_status = 3
    except AttributeError:
        logger.error("Mismatching configuration found")
        exit_status = 4
    except AssertionError:
        logger.error("Cannot find the queue submission command")
        exit_status = 5
    # pylint: disable=W0703
    except Exception as error:
        exit_status = 128
        logger.exception('Uncaught exception -> %s', repr(error))
    finally:
        parser.exit(exit_status)


if __name__ == "__main__":
    main()

# EOF
