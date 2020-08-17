#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   produce_gen_level.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   28.09.2017
# =============================================================================
"""Produce generator-level MC for acceptance calculations."""
from __future__ import print_function, division, absolute_import

import argparse
import os
from math import ceil

import analysis.utils.config as _config
import analysis.utils.paths as _paths
from analysis.batch import get_batch_system
from analysis.mc.gauss import get_gauss_version, get_gaudirun_options, get_db_tags
from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.efficiency.gen_level')

SCRIPT = """#!{shell}
#####################################
{header}
#####################################
echo "------------------------------------------------------------------------"
echo "Job started on" `date`
echo "------------------------------------------------------------------------"
set -e
if [ -f $HOME/.localrc ]; then
  source $HOME/.localrc
fi
source LbLogin.sh -c x86_64-slc6-gcc48-opt
source SetupProject.sh Gauss {gauss_version}
seed=`echo ${jobid_var} | cut -d'.' -f1`
echo "------------------------------------------------------------------------"
echo "Seed is "$seed
echo "------------------------------------------------------------------------"
# Prepare job
cd {workdir}
mkdir $seed
cd $seed
echo "Workdir: "$PWD
seedfile={workdir}/$seed/$seed.py
echo "from Configurables import GenInit, LHCbApp, Gauss
GaussGen = GenInit('GaussGen')
GaussGen.FirstEventNumber = 1
GaussGen.RunNumber = $seed
LHCbApp().EvtMax = {n_events}
LHCbApp().DDDBtag   = '{dddb_tag}'
LHCbApp().CondDBtag = '{conddb_tag}'
Gauss().DatasetName = '$seed'" > $seedfile
echo "Config file:"
cat $seedfile
# Run
gaudirun.py {gaudirun_options} $seedfile
# Move output
echo "Done"
ls -ltr
[ -d {output_path} ] || mkdir -p {output_path}
[ -d {output_path_link} ] || mkdir -p {output_path_link}
echo "Copying output to {output_path}"
cp $seed-*.{output_extension} {output_path}
cp $seed-*-histos.root {output_path}
output_gen_log={output_path_link}/${{seed}}_GeneratorLog.xml
echo "Copying GeneratorLog.xml : ${{output_gen_log}}"
cp GeneratorLog.xml ${{output_gen_log}}
echo "Copying output histos"
cp $seed-*-histos.root {output_path}
ls -ltr
# Do links
if [ "{do_link}" == true ]; then
    echo "Links requested to {output_path_link}"
    ln -sf {output_path}/$seed-* {output_path_link}/
fi
# Cleanup
rm -rf {workdir}/$seed
echo "------------------------------------------------------------------------"
echo "Job ended on" `date`
echo "------------------------------------------------------------------------"
"""


def run(config_files, link_from):
    """Run the script.

    Arguments:
        config_files (list[str]): Path to the configuration files.
        link_from (str): Path to link the results from.

    Return:
        int: Number of submitted jobs.

    Raise:
        OSError: If the configuration file does not exist.
        KeyError: If some configuration data are missing.
        ValueError: If no suitable batch backend is found.
        RuntimeError: If something goes wrong during submission.

    """
    try:
        config = _config.load_config(*config_files,
                                     validate=['event-type',
                                               'simulation-version',
                                               'year',
                                               'magnet-polarity',
                                               'prod/nevents',
                                               'prod/nevents-per-job'])
    except OSError:
        raise OSError("Cannot load configuration files: %s",
                      config_files)
    except _config.ConfigError as error:
        if 'event-type' in error.missing_keys:
            logger.error("No event type was specified in the config file!")
        if 'simulation-version' in error.missing_keys:
            logger.error("No simulation version was specified in the config file!")
        if 'year' in error.missing_keys:
            logger.error("No simulation year was specified in the config file!")
        if 'magnet-polarity' in error.missing_keys:
            logger.error("No magnet polarity was specified in the config file!")
        if 'prod/nevents' in error.missing_keys:
            logger.error("The number of events to produce was not specified in the config file!")
        if 'prod/nevents-per-job' in error.missing_keys:
            logger.error("The number of events per job was not specified in the config file!")
        raise KeyError("ConfigError raised -> %s" % error.missing_keys)
    except KeyError as error:
        logger.error("YAML parsing error -> %s", error)
        raise
    # Event type
    evt_type = config['event-type']
    try:
        evt_type = int(evt_type)
    except ValueError:  # There's non-numerical chars, we assume it's a path
        decfile = evt_type if os.path.isabs(evt_type) else os.path.abspath(evt_type)
        evt_type = os.path.splitext(os.path.split(decfile)[1])[0]
    else:
        decfile = '$DECFILESROOT/options/{}.py'.format(evt_type)
    # Prepare job
    _, _, log_file = _paths.prepare_path(name='mc/{}'.format(evt_type),
                                         path_func=_paths.get_log_path,
                                         link_from=link_from)  # No linking is done for logs
    # MC config
    sim_version = config['simulation-version'].lower()
    year = int(config['year'])
    magnet_polarity = config['magnet-polarity'].lower().lstrip('magnet').lstrip('mag')
    remove_detector = config.get('remove-detector', True)
    # Prepare paths
    do_link, output_path, output_path_link = _paths.prepare_path(name='',
                                                                 path_func=_paths.get_genlevel_mc_path,
                                                                 link_from=link_from,
                                                                 evt_type=evt_type,
                                                                 sim_version=sim_version,
                                                                 year=year,
                                                                 magnet_polarity=magnet_polarity,
                                                                 remove_detector=remove_detector)
    link_status = 'true' if do_link else 'false'
    try:
        options = get_gaudirun_options(sim_version,
                                       year,
                                       magnet_polarity,
                                       remove_detector)
        gauss_version = get_gauss_version(sim_version, year)
        dddb_tag, conddb_tag = get_db_tags(sim_version, year, magnet_polarity)
    except KeyError as error:
        logger.error("Unknown Gauss configuration")
        raise KeyError(str(error))
    # Add compression and our decfile
    options.append('$APPCONFIGOPTS/Persistency/Compression-ZLIB-1.py')
    options.append(decfile)
    # Prepare to submit
    nevents = min(config['prod']['nevents-per-job'], config['prod']['nevents'])
    logger.info("Generating %s events of decfile -> %s", nevents, decfile)
    logger.info("Output path: %s", output_path)
    logger.info("Log file location: %s", os.path.dirname(log_file))
    if do_link:
        logger.info("Linking to %s", output_path_link)
    extra_config = {'workdir': '$TMPDIR',
                    'do_link': link_status,
                    'gaudirun_options': ' '.join(options),
                    'gauss_version': gauss_version,
                    'dddb_tag': dddb_tag,
                    'conddb_tag': conddb_tag,
                    'output_extension': 'xgen' if remove_detector else 'sim',
                    'output_path': output_path,
                    'output_path_link': output_path_link,
                    'n_events': nevents}
    # Prepare batch
    batch_config = config.get('batch', {})
    try:
        batch_system = get_batch_system(batch_config.get('backend', None))
    except ValueError:
        raise
    # Submit
    njobs = int(ceil(1.0 * config['prod']['nevents'] / config['prod']['nevents-per-job']))
    logger.info("About to send %s jobs with %s events each.", njobs, nevents)
    for _ in range(njobs):
        # Submit
        try:
            job_id = batch_system.submit_job('MC_%s' % evt_type, SCRIPT, log_file,
                                             extra_config=extra_config,
                                             **batch_config)
            if 'submit error' in job_id:
                logger.error(job_id)
                raise Exception
            logger.debug("Submitted job -> %s", job_id)
        except Exception:
            logger.exception('Error submitting MC production job')
            raise RuntimeError
    return njobs


def main():
    """Generator level MC production application.

    Parses the command line and submits the MC production jobs.

    Status codes:
        0: All good.
        1: Missing configuration file.
        2: Error in the configuration file.
        3: No batch system found.
        4: Error in job submission.
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
    except OSError:
        logger.error("Configuration files missing!")
        exit_status = 1
    except KeyError:
        logger.error("Error in configuration file!")
        exit_status = 2
    except ValueError:
        logger.error("Cannot find a suitable batch system")
        exit_status = 3
    except RuntimeError:
        logger.error("Error in job submission")
        exit_status = 4
    # pylint: disable=W0703
    except Exception:
        logger.exception("Uncaught error")
        exit_status = 128
    finally:
        parser.exit(exit_status)


if __name__ == "__main__":
    main()

# EOF
