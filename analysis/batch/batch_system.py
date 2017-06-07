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
    SCRIPT = """
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

    def __init__(self):
        """Check that it has been properly subclassed."""
        assert self.SUBMIT_COMMAND
        assert self.DIRECTIVES

    def is_available(self):
        """Check if the bacth system is available.

        Returns:
            bool: If the batch system is available.

        """
        return which(self.SUBMIT_COMMAND) is not None

    # pylint: disable=too-many-locals
    def submit_job(self, job_name, cmd_script, script_args, log_file, **batch_config):
        """Submit a job to the batch system.

        The submission script is input as stdin.

        Arguments:
            job_name (str): Job name.
            cmd_script (str): Script to run.
            script_args (list): List of arguments passed to the script.
            log_file (str): Logfile location.
            runtime (str): Allocated time for the batch job.

        Returns:
            str: JobID.

        """
        cmd = 'python %s' % cmd_script
        cmd += ' %s' % (' '.join(script_args))
        # Format log file names
        err_file = batch_config.pop('errfile', log_file)
        log_file, ext = os.path.splitext(log_file)
        log_file = '%s%s.%s' % (log_file, self.JOBID_FORMAT, ext)
        err_file, ext = os.path.splitext(err_file)
        err_file = '%s%s.%s' % (err_file, self.JOBID_FORMAT, ext)
        # Build header
        header = [self.DIRECTIVES['shell'] % batch_config.pop('shell', '/bin/bash'),
                  self.DIRECTIVES['job-name'] % job_name,
                  self.DIRECTIVES['logfile'] % log_file,
                  self.DIRECTIVES['errfile'] % err_file,
                  self.DIRECTIVES['runtime'] % batch_config.pop('runtime', '02:00:00')]
        if log_file == err_file:
            header.append(self.DIRECTIVES['mergelogs'])
        for batch_option, batch_value in batch_config.items():
            directive = self.DIRECTIVES.get(batch_option, None)
            if directive is None:
                logger.warning("Ignoring directive %s -> %s", batch_option, batch_value)
                continue
            header.append(directive % batch_value)
        script = self.SCRIPT.format(workdir=os.getcwd(),
                                    script=cmd,
                                    header='\n'.join(header))
        # Submit using stdin
        logger.debug('Submitting -> %s', cmd)
        proc = subprocess.Popen(self.SUBMIT_COMMAND,
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE)
        output = proc.communicate(input=script)[0]
        return output.rstrip('\n')

    def get_job_id(self):
        return os.environ.get(self.JOBID_VARIABLE, None)


class Torque(BatchSystem):
    """Implement the Torque/PBS batch system."""

    SUBMIT_COMMAND = 'qsub'
    DIRECTIVES = {'shell': '#PBS -S %s',
                  'job-name': '#PBS -N %s',
                  'logfile': '#PBS -o %s',
                  'errfile': '#PBS -e %s',
                  'mergelogs': '#PBS -j oe',
                  'runtime': '#PBS -l cput=%s',
                  'memory': '#PBS -l mem=%s'}
    JOBID_FORMAT = '_${PBS_JOBID}'
    JOBID_VARIABLE = 'PBS_JOBID'


class Slurm(BatchSystem):
    """Implement the Slurm batch system."""

    SUBMIT_COMMAND = 'sbatch'
    DIRECTIVES = {'shell': '#SBATCH -S %s',
                  'job-name': '#SBATCH -N %s',
                  'logfile': '#SBATCH -o %s',
                  'errfile': '#SBATCH -e %s',
                  'mergelogs': '#SBATCH -j oe',
                  'runtime': '#SBATCH -l walltime=%s',
                  'memory': '#SBATCH --mem=%s',
                  'memory-per-cpu': '#SBATCH --mem-per-cpu=%s',
                  'queue': '#SBATCH --partition=%s'}
    JOBID_FORMAT = '_%j'
    JOBID_VARIABLE = 'SLURM_JOB_ID'


BATCH_SYSTEMS = OrderedDict((('slurm', Slurm()),
                             ('torque', Torque())))

# EOF
