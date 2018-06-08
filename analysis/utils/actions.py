#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# @file   actions.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   08.06.2018
# =============================================================================
"""Define actions in configuration files."""

from __future__ import print_function, division, absolute_import

import ROOT


def action_VAR(name, title, action_params, _):
    """Load a variable.

    This action is used for parameters without constraints. If one configuration
    element is given, the parameter doesn't have limits. If three are given, the last two
    specify the low and upper limits. Parameter is set to not constant.

    """
    # Take numerical value or load from file
    value_error = None
    if ':' in action_params[0]:  # We want to load a fit result
        from analysis.fit.result import FitResult
        fit_name, var_name = action_params[0].split(':')
        result = FitResult.from_yaml_file(fit_name)
        try:
            value, value_error, _, _ = result.get_fit_parameter(var_name)
        except KeyError:
            value = result.get_const_parameter(var_name)
    else:
        try:
            value = float(action_params[0])
        except ValueError:
            print("error, action params[0]", action_params[0])
    parameter = ROOT.RooRealVar(name, title, value)
    parameter.setConstant(False)
    if len(action_params) > 1:
        try:
            _, min_val, max_val = action_params
        except ValueError:
            raise ValueError("Wrongly specified var (need to give 1 or 3 arguments) "
                             "-> {}".format(action_params))
        parameter.setMin(float(min_val))
        parameter.setMax(float(max_val))
        parameter.setConstant(False)
    return parameter, None


def action_CONST(name, title, action_params, _):
    """Load a constant variable.

    Its argument indicates at which value to fix it.

    """
    # Take numerical value or load from file
    value_error = None
    if ':' in action_params[0]:  # We want to load a fit result
        from analysis.fit.result import FitResult
        fit_name, var_name = action_params[0].split(':')
        result = FitResult.from_yaml_file(fit_name)
        try:
            value, value_error, _, _ = result.get_fit_parameter(var_name)
        except KeyError:
            value = result.get_const_parameter(var_name)
    else:
        try:
            value = float(action_params[0])
        except ValueError:
            print("error, action params[0]", action_params[0])
    parameter = ROOT.RooRealVar(name, title, value)
    parameter.setConstant(True)
    return parameter, None


def action_GAUSS(name, title, action_params, _):
    """Load a variable with a Gaussian constraint.

    The arguments of that Gaussian, ie, its mean and sigma, are to be given
    as action parameters.

    """
    value_error = None
    if ':' in action_params[0]:  # We want to load a fit result
        from analysis.fit.result import FitResult
        fit_name, var_name = action_params[0].split(':')
        result = FitResult.from_yaml_file(fit_name)
        try:
            value, value_error, _, _ = result.get_fit_parameter(var_name)
        except KeyError:
            value = result.get_const_parameter(var_name)
    else:
        try:
            value = float(action_params[0])
        except ValueError:
            print("error, action params[0]", action_params[0])
    parameter = ROOT.RooRealVar(name, title, value)
    try:
        if len(action_params) == 1 and value_error is None:
            raise ValueError
        elif len(action_params) == 2:
            value_error = float(action_params[1])
        else:
            raise ValueError
    except ValueError:
        raise ValueError("Wrongly specified Gaussian constraint -> {}".format(action_params))
    constraint = ROOT.RooGaussian(name + 'Constraint',
                                  name + 'Constraint',
                                  parameter,
                                  ROOT.RooFit.RooConst(value),
                                  ROOT.RooFit.RooConst(value_error))
    parameter.setConstant(False)
    return parameter, constraint


def action_SHIFT(name, title, action_params, external_vars):
    """Configure a constant shift of a variable.

    The first param must be a shared variable, the second can be a number or a shared variable.

    """
    try:
        ref_var, second_var = action_params
    except ValueError:
        raise ValueError("Wrong number of arguments for SHIFT -> {}".format(action_params))
    try:
        if ref_var.startswith('@'):
            ref_var = ref_var[1:]
        else:
            raise ValueError("The first value for a SHIFT must be a reference.")
        ref_var, constraint = external_vars[ref_var]
        if second_var.startswith('@'):
            second_var = second_var[1:]
            second_var, const = external_vars[second_var]
            if not constraint:
                constraint = const
            else:
                raise NotImplementedError("Two constrained variables in SHIFT are not allowed")
        elif ':' in second_var:
            from analysis.fit.result import FitResult
            fit_name, var_name = second_var.split(':')
            result = FitResult.from_yaml_file(fit_name)
            try:
                value = result.get_fit_parameter(var_name)[0]
            except KeyError:
                value = result.get_const_parameter(var_name)
            second_var = ROOT.RooFit.RooConst(value)
        else:
            second_var = ROOT.RooFit.RooConst(float(second_var))
    except KeyError as error:
        raise ValueError("Missing parameter definition -> {}".format(error))
    parameter = ROOT.RooAddition(name, title, ROOT.RooArgList(ref_var, second_var))
    return parameter, constraint


def action_SCALE(name, title, action_params, external_vars):
    """Configure a constant scaling to a variable.

    The first param must be a shared variable, the second can be a number or a shared variable.

    """
    try:
        ref_var, second_var = action_params
    except ValueError:
        raise ValueError("Wrong number of arguments for SCALE -> {}".format(action_params))
    try:
        if ref_var.startswith('@'):
            ref_var = ref_var[1:]
        else:
            raise ValueError("The first value for a SCALE must be a reference.")
        ref_var, constraint = external_vars[ref_var]
        if second_var.startswith('@'):
            second_var = second_var[1:]
            second_var, const = external_vars[second_var]
            if not constraint:
                constraint = const
            else:
                raise NotImplementedError("Two constrained variables in SCALE are not allowed")
        elif ':' in second_var:
            from analysis.fit.result import FitResult
            fit_name, var_name = second_var.split(':')
            result = FitResult.from_yaml_file(fit_name)
            try:
                value = result.get_fit_parameter(var_name)[0]
            except KeyError:
                value = result.get_const_parameter(var_name)
            second_var = ROOT.RooFit.RooConst(value)
        else:
            second_var = ROOT.RooFit.RooConst(float(second_var))
    except KeyError as error:
        raise ValueError("Missing parameter definition -> {}".format(error))
    parameter = ROOT.RooProduct(name, title, ROOT.RooArgList(ref_var, second_var))
    return parameter, constraint


def action_RATIO(name, title, action_params, external_vars):
    """Configure a ratio between two variables.

    The first is the numerator, the second the denomiator. At least needs to be a shared variable,
    and currently two constrained variables are not possible.

    """
    from analysis.utils.pdf import load_pdf_by_name
    Ratio = load_pdf_by_name('RooRatio')

    if len(action_params) != 2:
        raise ValueError("Wrong number of arguments for RATIO -> {}".format(action_params))
    if not any(v.startswith('@') for v in action_params):
        raise ValueError("At least one parameter of a RATIO must be a reference")
    constraint = None
    processed_vars = []
    for variable in action_params:
        if variable.startswith('@'):
            processed_variable, const = external_vars[variable[1:]]
            if not constraint:
                constraint = const
            else:
                raise NotImplementedError("Two constrained variables in SCALE are not allowed")
        elif ':' in variable:
            from analysis.fit.result import FitResult
            fit_name, var_name = variable.split(':')
            result = FitResult.from_yaml_file(fit_name)
            try:
                value = result.get_fit_parameter(var_name)[0]
            except KeyError:
                value = result.get_const_parameter(var_name)
            processed_variable = ROOT.RooFit.RooConst(value)
        else:
            processed_variable = ROOT.RooFit.RooConst(float(variable))
        processed_vars.append(processed_variable)
    parameter = Ratio(name, title, *processed_vars)
    return parameter, constraint


def action_BLIND(name, title, action_params, external_vars):
    """Configure the blinding of a parameter using RooUnblindPrecision.

    The first parameter must be a shared variable whereas the following are a string and two floats.
    They represent a randomization string, a mean and a width (both used for the
    randomization of the value as well).

    """
    try:
        ref_var, blind_str, blind_central, blind_sigma = action_params
    except ValueError:
        raise ValueError("Wrong number of arguments for BLIND -> {}".format(action_params))
    try:
        if ref_var.startswith('@'):
            ref_var = ref_var[1:]
        else:
            raise ValueError("The first value for a BLIND must be a reference.")
        ref_var, constraint = external_vars[ref_var]
    except KeyError as error:
        raise ValueError("Missing parameter definition -> {}".format(error))
    parameter = ROOT.RooUnblindPrecision(name + "_blind", title + "_blind", blind_str,
                                         float(blind_central), float(blind_sigma), ref_var)
    return parameter, constraint


ACTION_KEYWORDS = {'VAR': action_VAR,
                   'CONST': action_CONST,
                   'GAUSS': action_GAUSS,
                   'SHIFT': action_SHIFT,
                   'SCALE': action_SCALE,
                   'RATIO': action_RATIO,
                   'BLIND': action_BLIND}

# EOF
