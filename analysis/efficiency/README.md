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
    - `plot`, which draws the projections of the efficiency.

Some models are already implemented by default, and are discussed in the following subsections.


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
    plots = eff.plot(data, {'acc_phi': r'$\phi$'})
    plots['acc_phi'].show()

```

It uses all the power of the `analysis` framework to fix the path, load the efficiency file and plot the acceptance.
