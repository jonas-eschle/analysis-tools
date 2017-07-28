Efficiency
==========

Classes helping the handling of efficiency models.
The essential function is `analysis.efficiency.get_efficiency_model`, which allows to load an efficiency model.
Irrespective of which particular model is used, the configuration of all efficiency models is the same:

```python
{'model': model_type,
 'variables': [var_1, var_2],
 'parameters': {model_config}
}
```

and its equivalent in YAML.
The `model_type` defines the type of efficiency parametrization, implemented through a class inheriting from `analyisis.efficiency.efficiency.Efficiency`;
the `variables` list defines which variables from the input datasets the efficiency belongs to;
and the `parameters` dictionary configures the `Efficiency` object, and will be different for every type of parametrization.

A `load_efficiency_model` class is also provided, allowing to load previously calculated efficiency models from disk.
These are saved using the `Efficiency.write_to_disk` method, with the path of the file determined using the `analysis.utils.paths.get_efficiency_path` function.

In general, the `Efficiency` class is initialized by giving it the variable list and the configuration (what is stored in parameters `parameters`).
Additionally, when using `get_efficiency_model` one can specify a `rename-vars` map that allows to rename the variable names when the `model_config` has been loaded from file;
this allows to match variable names when using different datasets.

To implement an efficiency model, one needs to subclass `Efficiency` and implement the following methods:

    - `_get_efficiency`, which calculates the value of the efficiency given a dataset.
    - `fit`, to model a given dataset with the efficiency model.
    - `project_efficiency`, which draws the projections of the efficiency.

Some models are already implemented by default, and are discussed in the following subsections.

**Note**: To implement your own efficiency model, look at `legendre.py` as an example. It's important to remember to use `get_variables` and `get_variable_names` to get the variable names to ensure that they can be renamed and everything still works.

Legendre
--------

Model the efficiencies using Legendre polynomials:
the `LegendreEfficiency` class implements a fully correlated n-D model, while `LegendreEfficiency1D` implements independent 1D modelling.

A full example on how to model a 4D acceptance using Legendre polynomials and then doing a plot is the following:

```python
import os
from logging import DEBUG

import pandas as pd

from analysis.efficiency import load_efficiency_model, get_efficiency_model_class
from analysis.utils.monitoring import Timer
from analysis.utils.paths import get_efficiency_path
from analysis.utils.logging_color import get_logger

EFF_NAME = 'Test'

logger = get_logger('efficiency_test', DEBUG)
get_logger('analysis.efficiency.legendre').setLevel(DEBUG)

var_list = ['acc_q2',
            'acc_cosThetaL',
            'acc_cosThetaK',
            'acc_phi']

orders = {'acc_q2': 1,
          'acc_cosThetaL': 5,
          'acc_cosThetaK': 10,
          'acc_phi': 10}

with pd.HDFStore('B02Kst0Jpsi2ee-Gen.h5') as store:
    # Slow, it's a large file!
    logger.info("Loading data")
    data = store.select('B02Kst0Jpsi2ee-Gen', columns=var_list)
    if not os.path.exists(get_efficiency_path(EFF_NAME)):
        EffClass = get_efficiency_model_class('legendre')
        with Timer() as timer:
            eff = EffClass.fit(data,
                               var_list,
                               legendre_orders=orders,
                               ranges={'acc_phi': ['-pi', 'pi'],
                                       'acc_q2': [8, 11]})
            logger.info("Took %s ms / %s coefficients",
                        timer.elapsed, eff.get_coefficients().size)
        out_file = eff.write_to_disk(EFF_NAME)
        logger.info("Written efficiency file -> %s", out_file)
    else:
        logger.info("Loading coeffs -> %s", EFF_NAME)
        eff = load_efficiency_model(EFF_NAME)
    plots = eff.plot(data, labels={'acc_phi': r'$\phi$'})
    plots['acc_phi'].show()

```

It uses all the power of the `analysis` framework to fix the path, load the efficiency file and plot the acceptance.


Modeling efficiency
-------------------

The `model_efficiency` script gives a shortcut to what was discussed in the previous section.
With it, one could perform the same job as in the previous code with the following configuration file:

```yaml
name: Test
model: legendre
data: 
    source: B02Kst0Jpsi2ee-Gen.h5
    tree: B02Kst0Jpsi2ee-Gen
variables:
  - acc_q2
  - acc_cosThetaL
  - acc_cosThetaK
  - acc_phi
parameters:
    legendre-orders:
        acc_q2: 1
        acc_cosThetaL: 5
        acc_cosThetaK: 10
        acc_phi: 10
    ranges:
        acc_phi: -pi pi
        acc_q2: 8 11
plot: y
plot-labels:
    acc_q2: '$q^2$ (GeV$^2/c^4$)'
    acc_cosThetaL: '$cos\theta_K$'
    acc_cosThetaK: '$cos\theta_\ell$'
    acc_phi: '$\phi$ (rad)'
```

A weight variable can be specified in `data/weight`.

This has the advantage of taking care of saving the plots `$BASE_PATH/data/efficiency/{name}_{var}.eps` and handling the errors in a more graceful way.


Acceptance
==========

Manage acceptance corrections.
The basic function is `analysis.efficiency.get_acceptance`, which loads two efficiency models (numerator and denominator, called `reconstruction` and `generation`, respectively) and returns an `Acceptance` instance that can be used to calculate weights or perform accept-reject.

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

