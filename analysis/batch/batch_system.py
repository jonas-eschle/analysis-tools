#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   batch_system.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   31.05.2017
# =============================================================================
"""Implementation of different batch systems."""

import os
import subprocess
from collections import OrderedDict

from analysis.utils.logging_color import get_logger


logger = get_logger('analysis.batch.batch_system')


def which(program):
    """Check the location of the given command.

    Arguments:
        program (str): Command to check.

    Returns:
        str: Path of the program. Returns None if it cannot be found.

    """
    def is_exe(fpath):
        """Check if path is executable."""
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    if os.path.split(program)[0]:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


class BatchSystem(object):
    """Batch System base class."""

    SUBMIT_COMMAND = None
    DEFAULT_SCRIPT = """#!{shell}
#####################################
{header}
#####################################
echo "------------------------------------------------------------------------"
echo "Job started on" `date`
echo "------------------------------------------------------------------------"
if [ -f $HOME/.localrc ]; then
  source $HOME/.localrc
fi
cd {workdir}
echo $PWD
{script}
echo "------------------------------------------------------------------------"
echo "Job ended on" `date`
echo "------------------------------------------------------------------------"
"""
    DIRECTIVES = {}
    JOBID_FORMAT = ''
    JOBID_VARIABLE = ''

    def __init__(self):
        """Check that it has been properly subclassed."""
        assert self.SUBMIT_COMMAND
        assert self.DIRECTIVES
        assert self.JOBID_FORMAT
        assert self.JOBID_VARIABLE

    def is_available(self):
        """Check if the bacth system is available.

        Returns:
            bool: If the batch system is available.

        """
        return which(self.SUBMIT_COMMAND) is not None

    def submit_job(self, job_name, script, log_file, extra_config=None, **batch_config):
        """Submit a job to the batch system.

        Arguments:
            job_name (str): Job name.
            script (str): Commands to run.
            script_args (list): List of arguments passed to the script.
            log_file (str): Logfile location.
            extra_config (dict, optional): Extra configuration for 'script'. Defaults
                to `None`.
            **batch_config (dict): Configuration of the batch system.

        Returns:
            str: Job ID

        """
        err_file = batch_config.pop('errfile', log_file)
        log_file, ext = os.path.splitext(log_file)
        log_file = '{}{}{}'.format(log_file, self.JOBID_FORMAT, ext)
        err_file, ext = os.path.splitext(err_file)
        err_file = '{}{}{}'.format(err_file, self.JOBID_FORMAT, ext)
        # Build header
        header = [self.DIRECTIVES['job-name'].format(job_name),
                  self.DIRECTIVES['logfile'].format(log_file),
                  self.DIRECTIVES['errfile'].format(err_file),
                  self.DIRECTIVES['runtime'].format(batch_config.pop('runtime', '01:00:00'))]
        if log_file == err_file:
            header.append(self.DIRECTIVES['mergelogs'])
        for batch_option, batch_value in batch_config.items():
            directive = self.DIRECTIVES.get(batch_option, None)
            if directive is None:
                logger.warning("Ignoring directive %s -> %s", batch_option, batch_value)
                continue
            header.append(directive % batch_value)
        script_config = extra_config if extra_config is not None else {}
        script_config['workdir'] = script_config.get('workdir', os.getcwd())
        script_config['header'] = '\n'.join(header)
        script_config['shell'] = batch_config.pop('shell', '/bin/bash')
        script_config['jobid_var'] = self.JOBID_VARIABLE
        # Submit using stdin
        logger.debug('Submitting job')
        proc = subprocess.Popen(self.SUBMIT_COMMAND,
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE)
        return proc.communicate(input=script.format(**script_config))[0].rstrip('\n')

    # pylint: disable=too-many-arguments
    def submit_script(self, job_name, cmd_script, script_args,
                      log_file, executable='python', **batch_config):
        """Submit a job to the batch system.

        The submission script is input as stdin.

        Arguments:
            job_name (str): Job name.
            cmd_script (str): Script to run.
            script_args (list): List of arguments passed to the script.
            log_file (str): Logfile location.
            executable (str, optional): Command to execute the script. Defaults to 'python'.
            **batch_config (dict): Configuration of the batch system.

        Returns:
            str: JobID.

        """
        cmd = '{} {} {}'.format(executable + ' ' if executable else './',
                                cmd_script,
                                ' '.join(script_args))
        return self.submit_job(job_name, self.DEFAULT_SCRIPT, log_file, extra_config={'script': cmd}, **batch_config)

    def get_job_id(self):
        """Get the Job ID.

        Only works if we are in the batch system.

        Returns:
            str: Job ID.

        """
        return os.environ.get(self.JOBID_VARIABLE, None)


class Torque(BatchSystem):
    """Implement the Torque/PBS batch system."""

    SUBMIT_COMMAND = 'qsub'
    DIRECTIVES = {'job-name': '#PBS -N {}',
                  'logfile': '#PBS -o {}',
                  'errfile': '#PBS -e {}',
                  'mergelogs': '#PBS -j oe',
                  'runtime': '#PBS -l cput={0}\n#PBS -l walltime={0}',
                  'memory': '#PBS -l mem={}'}
    JOBID_FORMAT = '_${PBS_JOBID}'
    JOBID_VARIABLE = 'PBS_JOBID'


class Slurm(BatchSystem):
    """Implement the Slurm batch system."""

    SUBMIT_COMMAND = 'sbatch'
    DIRECTIVES = {'job-name': '#SBATCH -J {}',
                  'logfile': '#SBATCH -o {}',
                  'errfile': '#SBATCH -e {}',
                  'mergelogs': '',
                  'runtime': '#SBATCH -t {}',
                  'memory': '#SBATCH --mem={}',
                  'memory-per-cpu': '#SBATCH --mem-per-cpu={}',
                  'queue': '#SBATCH --partition={}'}
    JOBID_FORMAT = '_%j'
    JOBID_VARIABLE = 'SLURM_JOB_ID'


BATCH_SYSTEMS = OrderedDict((('slurm', Slurm()),
                             ('torque', Torque())))

# EOF
