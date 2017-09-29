#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   produce_gen_level.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   28.09.2017
# =============================================================================
"""Produce generator-level MC for acceptance calculations."""

import argparse
import os
from math import ceil

import analysis.utils.paths as _paths
import analysis.utils.config as _config
from analysis.batch import get_batch_system
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
#  source LbLogin.sh -c x86_64-slc5-gcc46-opt
source SetupProject.sh Gauss v49r8
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
echo "from Configurables import GenInit,LHCbApp,Gauss
GaussGen = GenInit('GaussGen')
GaussGen.FirstEventNumber = 1
GaussGen.RunNumber        = $seed
LHCbApp().EvtMax = {n_events}
Gauss().DatasetName = '$seed'" > $seedfile
echo "Config file:"
cat $seedfile
# Run
gaudirun.py $GAUSSOPTS/Gauss-Job.py $GAUSSOPTS/Gauss-2012.py $GAUSSOPTS/GenStandAlone.py {decfile} $LBPYTHIA8ROOT/options/Pythia8.py $seedfile
# Move output
mv $seed-*.xgen {output_file}
mv $seed-*-histos.root {output_histos}
ls -ltr
# Do links
if [ "{do_link}" == true ]; then
    ln -sf {output_file} {output_file_link}
    ln -sf {output_histos} {output_histos_link}
if
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

    Returns:
        int: Number of submitted jobs.

    Raises:
        OSError: If the configuration file does not exist.
        KeyError: If some configuration data are missing.
        ValueError: If no suitable batch backend is found.
        RuntimeError: If something goes wrong during submission.

    """
    try:
        config = _config.load_config(*config_files,
                                     validate=['event-type',
                                               'prod/nevents',
                                               'prod/nevents-per-job'])
    except OSError:
        raise OSError("Cannot load configuration files: %s",
                      config_files)
    except _config.ConfigError as error:
        if 'event-type' in error.missing_keys:
            logger.error("No event type was specified in the config file!")
        if 'prod/nevents' in error.missing_keys:
            logger.error("The number of events to produce was not specified in the config file!")
        if 'prod/nevents-per-job' in error.missing_keys:
            logger.error("The number of events per job was not specified in the config file!")
        raise KeyError("ConfigError raised -> %s" % error.missing_keys)
    except KeyError as error:
        logger.error("YAML parsing error -> %s", error)
        raise
    # Locate decfile
    try:
        evt_type = int(config['event-type'])
    except ValueError:  # There's non-numerical chars, we assume it's a path
        if not os.path.isabs(evt_type):
            evt_type = os.path.abspath(evt_type)
        decfile = evt_type
    else:
        decfile = '$DECFILESROOT/options/{}.py'.format(evt_type)
    # Prepare job
    _, _, log_file = _paths.prepare_path('mc/{}'.format(evt_type),
                                         _paths.get_log_path,
                                         None)  # No linking is done for logs
    do_link, output_file, output_file_link = _paths.prepare_path('{}_$seed'.format(evt_type),
                                                                 _paths.get_genlevel_mc_path,
                                                                 link_from,
                                                                 evt_type=evt_type)
    _, output_histos, output_histos_link = _paths.prepare_path('{}_$seed'.format(evt_type),
                                                               _paths.get_genlevel_histos_path,
                                                               link_from,
                                                               evt_type=evt_type)
    link_status = 'true' if do_link else 'false'
    extra_config = {'workdir': '$TMPDIR',
                    'do_link': link_status,
                    'output_file': output_file,
                    'output_file_link': output_file_link,
                    'output_histos': output_histos,
                    'output_histos_link': output_histos_link,
                    'decfile': decfile,
                    'n_events': config['prod']['nevents-per-job']}
    # Prepare batch
    batch_config = config.get('batch', {})
    try:
        batch_system = get_batch_system(batch_config.get('backend', None))
    except ValueError:
        raise
    # Submit
    njobs = int(ceil(1.0*config['prod']['nevents']/config['prod']['nevents-per-job']))
    for _ in range(njobs):
        # Submit
        try:
            job_id = batch_system.submit_job('MC_%s' % evt_type, SCRIPT, log_file,
                                             extra_config=extra_config,
                                             **batch_config)
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
