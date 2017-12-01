Fit
===

Configure fit-related analysis elements.



Register fit strategies
-----------------------

A *fit strategy* consists of a function that gets a PDF model, a dataset to fit and the fit options, and returns a `RooFitResult`.
Complicated fit strategies can the be built, optionally containing constraints (using `utils.config.configure_parameter` for example), and are registered using the `analysis.fit.register_fit_strategy` function.

As an example, the default fit strategy, called `simple`, is defined with:

```python
from analysis.fit import register_fit_strategy
register_fit_strategy('simple',
                      lambda model, dataset, fit_config: model.fitTo(dataset, *fit_config))
```

More complicated functions can also be used.


Fitting datasets
----------------

The script `fit_dataset.py` can be used to directly fit a given dataset with a given configuration.
It can additionally be used to save the fit result and perform *sPlots* (plots will come in the future).

Fits are very easy to configure:

  + A `name` is given, which will be used to save the fit result if requested.
  + The PDF model is given in the `model` key and specified [in the usual way](../physics/README.md).
  + The data to fit is specified [in the usual way](../data/README.md) under the `data` key.
  + The *sPlot* configuration is specified under the `splot` key, and can have three elements:
  `components-to-splot` is a list of the components that we want to get *sPlot* weights for;
  `output-file` is the name of the output file if we want to save the *sPlotted* dataset (if it's an absolute path, it will be used directly, if not, the `get_splot_path` function is used);
  and the optional `overwrite` key defined if older *sPlot* datasets with the same name are removed before saving the new one (default is `False`, so the script will throw an error if the file is present).
=======
Types: @string/string/string/string *(followed by params as needed for Roo variable config)*
Meaning: @reference_name/variable_name/variable_title/type (type is the exact config
syntax for a variable)
Example: @mu1_low/mu1/mu_the_lower/VAR 50 10 90 (shared variable of type VAR)

Usage examples:
just the reference: @mu1_low
within another variable: SHIFT @mu1_low 2701 (shift the value 2071 by @mu1_low)
