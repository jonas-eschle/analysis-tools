Acceptance
==========

Manage acceptance corrections.
The basic function is `analysis.acceptance.get_acceptance`, which loads two efficiency models (numerator and denominator, called `reconstruction` and `generation`, respectively) and returns an `Acceptance` instance that can be used to calculate weights or perform accept-reject.

The configuration required by this function is:

```python
{'variables': [var_1, var_2],
 'generation': {'name': gen_name,
                'rename-vars': {gen_var1: var1}},
 'reconstruction': {'name': rec_name,
                    'rename-vars': {rec_var1: var1}}}
```

and its equivalent in YAML (which can be called using the `load_acceptance` function).
The `variables` key defines which variables from the input datasets are used;
the `generation` and `reconstruction` keys define the name of numerator and denominator efficiencies, respectively, loaded using `analysis.efficiencies.load_efficiency_model` with the addition of `rename-vars`, which can be used to redefine the names of the variables used in the efficiencies to match those in the `variables` entry.

The `Acceptance` class provides two main methods:

  - `apply_accept_reject`, which takes a dataset and filters it according to the configured acceptance.
  - `get_weights`, which returns the weights of the input dataset according to the efficiency.

