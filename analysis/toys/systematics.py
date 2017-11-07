#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   systematics.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   30.10.2017
# =============================================================================
"""Systematic uncertainty toy generators."""

from collections import OrderedDict

import numpy as np

from analysis.fit.result import FitResult
from analysis.utils.root import list_to_rooargset, iterate_roocollection
from analysis.data.mergers import merge_root
from analysis import get_global_var
from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.toys.systematics')


def register_systematic(name, syst_class):
    """Register a systematic toy generator.

    Systematics are registered in the `TOY_SYSTEMATICS` global variable.

    Arguments:
        name (str): Name of the systematic.
        syst_class (Systematic): Systematic generator class to register.

    Return:
        int: Number of registered systematics.

    Raise:
        ValueError: If `syst_class` is not of the correct type.

    """
    logger.debug("Registering %s systematic generator", name)
    if not isinstance(syst_class, Systematic):
        raise ValueError("Wrong class type -> {}".format(type(syst_class)))
    get_global_var('TOY_SYSTEMATICS').update({name: syst_class})
    return len(get_global_var('TOY_SYSTEMATICS'))


def get_systematic(syst_config):
    """Load systematic toy generator.

    The systematic type is specified through the `type` key.

    Arguments:
        syst_config (dict): Configuration of the systematic toy.

    Return:
        Systematic class

    Raise:
        KeyError: If the systematic type is unknown.

    """
    return get_global_var('TOY_SYSTEMATICS')[syst_config['type']]


class Systematic(object):
    """Base class for systematics."""

    def __init__(self, model, config):
        """Configure systematic.

        The physics model needs to be extended. In case it isn't, `yield` needs to
        be specified in `config`.

        Arguments:
            model (`analysis.physics.PhysicsFactory`): Factory used for generation and
                fitting.
            config (dict): Configuration.

        Raise:
            ValueError: If no yield is specified, either through the PDF model or the
                configuration.

        """
        self._model = model
        if model.is_extended():
            self._gen_pdfs = [model.get_extended_pdf("GenSystPdf", "GenSystPdf")]
        else:
            try:
                self._gen_pdfs = [model.get_extended_pdf("GenSystPdf", "GenSystPdf", config['yield'])]
            except KeyError:
                raise ValueError("No yield specified")
        self._input_values = None
        self._config = config

    def get_dataset(self, acceptance, randomize=True):
        """Get dataset generated from the input model.

        If an acceptance is given, accept-reject is applied on the dataset, and an extra variable
        representing the inverse of the per-event weight (`fit_weight`) is added as weight.

        Arguments:
            acceptance (analysis.efficiency.acceptance.Acceptance): Acceptance object. If `None`
                is given, no acceptance is applied.
            randomize (bool, optional): Randomize the parameters according to the systematic.
                Defaults to `True`.

        Return:
            `ROOT.RooDataSet`.

        """
        # TODO: Add weights, acceptance. If weights/acceptance, loop and generate one by one.
        if randomize:
            self.randomize()
        if not acceptance:
            return merge_root([pdf.generate(list_to_rooargset(self._model.get_observables()))
                               for pdf in self._gen_pdfs],
                              'GenData', 'GenData')
        else:
            raise NotImplementedError("Acceptance not implemented yet")

    def randomize(self):
        """Randomize the parameters relevant for the systematic calculation.

        This function modifies the internal parameters of the generator PDF, so doesn't
        return their values.

        Return:
            int: Number of randomized parameters.

        """
        raise NotImplementedError("randomize needs to be implemented by each systematics class")

    def get_input_values(self):
        """Get the original values of the input model.

        Return:
            dict

        """
        if self._input_values is None:
            self._input_values = {var.GetName(): [var.getVal()]
                                  for var in self._model.get_gen_parameters() + self._model.get_yield_vars()}
        return self._input_values


class FixedParamsSyst(Systematic):
    """Systematic for parameters fixed from simulation or other models."""

    def __init__(self, model, config):
        """Configure systematic.

        To specify where the parameters come from, `config` needs a `syst` key which contains
        a list of results and parameter name correspondences to be used to translate from the
        fit result to `model`.

            {'syst': [{'result': result_name,
                       'param_names': {'fit_result_name': 'model_parameter_name',
                                       ...}},
                       ...]}

        Arguments:
            model (`analysis.physics.PhysicsFactory`): Factory used for generation and
                fitting.
            config (dict): Configuration.

        Raise:
            KeyError: If some systematic configuration parameter is missing.
            RuntimeError: If the parameter names are badly specified.
            ValueError: If no yield is specified, either through the PDF model or the
                configuration.

        """
        def make_block(*matrices):
            """Make bloc-diagonal matrix.

            Arguments:
                matrices (list): Matrices to combine.

            Return:
                numpy.ndarray: Block-diagonal matrix.

            """
            dimensions = sum(mat.shape[0] for mat in matrices), sum(mat.shape[1] for mat in matrices)
            output_mat = np.zeros(dimensions)
            row = 0
            column = 0
            for mat in matrices:
                output_mat[row:row+mat.shape[0], column:column+mat.shape[1]] = mat
                row = row+mat.shape[0]
                column = column+mat.shape[1]
            return output_mat

        super(FixedParamsSyst, self).__init__(model=model, config=config)
        cov_matrices = []
        central_values = []
        self._param_translation = OrderedDict()
        # Load fit results and their covariance matrices
        for result_config in config['syst']:
            fit_result = FitResult().from_yaml_file(result_config['result'])
            self._param_translation.update(result_config['param_names'])
            cov_matrices.append(fit_result.get_covariance_matrix(self._param_translation.keys()))
            central_values.append(np.diag([float(fit_result.get_fit_parameter(param)[0])
                                           for param in self._param_translation.keys()]))
        # Check that there is a correspondence between the fit result and parameters in the generation PDF
        self._cov_matrix = make_block(*cov_matrices)
        self._central_values = make_block(*central_values)
        self._pdf_index = {}
        for fit_param in self._param_translation.values():
            found = False
            for pdf_num, pdf in enumerate(self._gen_pdfs):
                if fit_param in [var.GetName() for var in iterate_roocollection(pdf.getVariables())]:
                    self._pdf_index[fit_param] = pdf_num
                    found = True
                    break
            if not found:
                raise RuntimeError("Cannot find parameter {} in the physics model".format(fit_param))

    def randomize(self):
        """Randomize the fit parameters according to the covariance matrix.

        This function modifies the internal parameters of the generator PDF, so doesn't
        return their values.

        Return:
            int: Number of randomized parameters.

        """
        random_values = np.random.multivariate_normal(self._central_values, self._cov_matrix)
        for param_num, (param_name, pdf_index) in enumerate(self._pdf_index.items()):
            self._gen_pdfs[pdf_index].getVariables[param_name].setVal(random_values[param_num])
        return len(random_values)

# EOF
