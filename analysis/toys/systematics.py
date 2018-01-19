#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# @file   systematics.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   30.10.2017
# =============================================================================
"""Systematic uncertainty toy generators."""
from __future__ import print_function, division, absolute_import

from collections import OrderedDict, defaultdict

import numpy as np
from scipy.stats import poisson

import ROOT

from analysis.fit.result import FitResult
from analysis.utils.root import list_to_rooargset, list_to_rooarglist, iterate_roocollection
from analysis.data.mergers import merge_root
from analysis.data.converters import pandas_from_dataset, dataset_from_pandas
from analysis.utils.logging_color import get_logger

logger = get_logger('analysis.toys.systematics')


class SystematicToys(object):
    """Base class for systematics."""

    def __init__(self, model, config=None, acceptance=None):
        """Configure systematic.

        The physics model needs to be extended. In case it isn't, `yield` needs to
        be specified in `config`. For simultaneous PDFs, `yield` needs to be a
        dictionary matching categories with their corresponding yield.

        Arguments:
            model (`analysis.physics.PhysicsFactory`): Factory used for generation and
                fitting.
            acceptance (`analysis.efficiency.acceptance.Acceptance`): Acceptance to apply.
                Can be `None`.
            config (dict, optional): Configuration. Defaults to None.
            acceptance (analysis.efficiency.acceptance.Acceptance): Generation acceptance.
                Defaults to `None`.

        Raise:
            ValueError: If no yield is specified, either through the PDF model or the
                configuration.

        """
        def get_pdfs_to_generate(pdf_model, pdf_config):
            """Split the PDF model into PDFs that need to be generated independently.

            Arguments:
                pdf_model (analysis.physics.factory.PhysicsFactory): Model to splot.
                pdf_config (dict): Extra configuration. Currently, only the `yield` key
                    is used.

            Return:
                dict: PDFs split by label. If the model is not simultaneous, all PDFs are
                    under label `None`.

            Raise:
                ValueError: If no yield is specified, either through the PDF model or the
                    configuration.

            """
            if not pdf_model.is_extended():
                try:
                    if pdf_model.is_simultaneous():
                        if set(pdf_model.get_children.keys()) != set(pdf_config['yield'].keys()):
                            raise ValueError("PDF labels don't match yield labels")
                        return {label: [child.get_extended_pdf("GenSystPdf_{}".format(label),
                                                               "GenSystPdf_{}".format(label),
                                                               pdf_config['yield'][label])]
                                for label, child in pdf_model.get_children().items()}
                    else:
                        return {None: [pdf_model.get_extended_pdf("GenSystPdf", "GenSystPdf", config['yield'])]}
                except (KeyError, AttributeError):
                    raise ValueError("Yield badly specified")
            else:
                if pdf_model.get_children() and \
                        all(child.is_extended() for child in pdf_model.get_children().values()):
                    output = defaultdict(list)
                    for label, child in pdf_model.get_children().items():
                        if pdf_model.is_simultaneous():
                            output[label] = get_pdfs_to_generate(child, None)[None]
                        else:
                            output[None].extend(get_pdfs_to_generate(child, None)[None])
                    return output
                return {None: [pdf_model.get_extended_pdf("GenSystPdf", "GenSystPdf")]}

        if config is None:
            config = {}
        self._gen_pdfs = get_pdfs_to_generate(model, config)
        logger.debug("Determined split PDFs to generate -> %s", self._gen_pdfs)
        self._model = model
        self._input_values = None
        self._config = config
        self._gen_acceptance = acceptance
        self._fit_acceptance = acceptance

    def get_dataset(self, randomize=True):
        """Get dataset generated from the input model.

        If an acceptance was given on initialization, accept-reject is applied on the dataset,
        and an extra variable representing the inverse of the per-event weight (`fit_weight`)
        is added as weight.

        Arguments:
            randomize (bool, optional): Randomize the parameters according to the systematic.
                Defaults to `True`.

        Return:
            `ROOT.RooDataSet`.

        """
        # TODO: Add weights?
        if randomize:
            logger.debug("Applying randomization")
            self.randomize()
        obs = list_to_rooargset(self._model.get_observables())
        datasets_to_merge = []
        cats = list_to_rooarglist(self._model.get_category_vars())
        for label, pdf_list in self._gen_pdfs.items():
            if cats:
                for lab_num, lab in enumerate(label.split(',')):
                    cats[lab_num].setLabel(lab)
            for pdf in pdf_list:
                logger.debug("Generating PDF -> %s", pdf.GetName())
                if self._gen_acceptance:
                    # TODO: Fixed yields
                    yield_to_generate = poisson.rvs(pdf.expectedEvents(obs))
                    pandas_dataset = None
                    while yield_to_generate:
                        events = self._gen_acceptance.apply_accept_reject(
                            pandas_from_dataset(
                                pdf.generate(obs, yield_to_generate*2)))
                        # Sample if the dataset is too large
                        if events.shape[0] > yield_to_generate:
                            events = events.sample(yield_to_generate)
                        # Merge with existing
                        if not pandas_dataset:
                            pandas_dataset = events
                        else:
                            pandas_dataset = pandas_dataset.append(events, ignore_index=True)
                        yield_to_generate -= len(events)
                    logger.debug("Adding fitting weights")
                    pandas_dataset['fit_weight'] = self._fit_acceptance.get_fit_weights(pandas_dataset)
                    dataset = dataset_from_pandas(pandas_dataset, "GenData", "GenData", weight_var='fit_weight')
                else:
                    dataset = pdf.generate(obs, ROOT.RooFit.Extended(True))
                if cats:
                    dataset.addColumns(cats)
                datasets_to_merge.append(dataset)
        return merge_root(datasets_to_merge, 'GenData', 'GenData')

    def randomize(self):
        """Randomize the parameters relevant for the systematic calculation.

        This function modifies the internal parameters of the generator PDF, so
        it doesn't return their values but the number of randomized parameters.

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
            self._input_values = {"{}_gen".format(var.GetName()): [var.getVal()]
                                  for var in list(self._model.get_gen_parameters()) + self._model.get_yield_vars()}
        return self._input_values


class FixedParamsSyst(SystematicToys):
    """Systematic for parameters fixed from simulation or other models."""

    def __init__(self, model, acceptance, config):
        """Configure systematic.

        To specify where the parameters come from, `config` needs a `params` key which contains
        a list of results and parameter name correspondences to be used to translate from the
        fit result to `model`.

            {'params': [{'result': result_name,
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

        super(FixedParamsSyst, self).__init__(model, config=config, acceptance=acceptance)
        cov_matrices = []
        central_values = []
        param_translation = OrderedDict()
        # Load fit results and their covariance matrices
        syst = config['params']
        if not isinstance(syst, (list, tuple)):
            syst = [syst]
        for result_config in syst:
            fit_result = FitResult.from_yaml_file(result_config['result'])
            param_translation.update(result_config['param_names'])
            cov_matrices.append(fit_result.get_covariance_matrix(param_translation.keys()))
            central_values.extend([float(fit_result.get_fit_parameter(param)[0])
                                           for param in param_translation.keys()])
        # Check that there is a correspondence between the fit result and parameters in the generation PDF
        self._cov_matrix = make_block(*cov_matrices)
        self._central_values = np.array(central_values)
        self._pdf_index = {}
        for fit_param in param_translation.values():
            found = False
            for label, pdf_list in self._gen_pdfs.items():
                for pdf_num, pdf in enumerate(pdf_list):
                    if fit_param in [var.GetName() for var in iterate_roocollection(pdf.getVariables())]:
                        self._pdf_index[fit_param] = (label, pdf_num)
                        found = True
                        break
                if found:
                    break
            if not found:
                raise RuntimeError("Cannot find parameter {} in the physics model".format(fit_param))

    def randomize(self):
        """Randomize the fit parameters according to the covariance matrix.

        This function modifies the internal parameters of the generator PDF, so
        it doesn't return their values but the number of randomized parameters.

        Return:
            int: Number of randomized parameters.

        """
        random_values = np.random.multivariate_normal(self._central_values, self._cov_matrix)
        for param_num, (param_name, pdf_index) in enumerate(self._pdf_index.items()):
            pdf_label, pdf_num = pdf_index
            self._gen_pdfs[pdf_label][pdf_num].getVariables()[param_name].setVal(random_values[param_num])
        return len(random_values)


class AcceptanceSyst(SystematicToys):
    """Systematic toys for acceptance parameters."""
    def randomize(self):
        """Randomize the acceptance function.

        The fit acceptance is randomized and stored as generation acceptance.

        Return:
            const: 2 (the number of randomized matrices).

        Raise:
            ValueError: Problem randomizing the acceptance.

        """
        try:
            self._gen_acceptance = self._fit_acceptance.randomize()
        except NotImplementedError:
            logger.error("Randomization not supported by the acceptance")
            raise ValueError("Error randomizing systematic")
        except ValueError as error:
            logger.error("Error randomizing acceptance -> %s", str(error))
            raise ValueError("Error randomizing systematic")
        return 2


SYSTEMATIC_TOYS = {'fixed_params': FixedParamsSyst,
                   'acceptance': AcceptanceSyst}

# EOF
