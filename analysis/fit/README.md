Fit
===

Configure PDF- and fit-related analysis elements.


Load PDFs
---------

Models can be loaded using the `load_pdfs` function, which is configured from a single dictionary (which can come from a YAML file).
Each entry of the dictionary defines one `PhysicsFactory` (the key being its name and the value its configuration), and all entries are added using a `RooAddPdf` after converting each PDF into an `RooExtendPdf`.

More specifically, the `pdfs` key in each of the entries is used to configure the `PhysicsFactory`, which is configured in the usual way (see the [corresponding `README.md`](../physics/README.md) file).
Additional constraints on the PDF parameter values can be imposed when using `load_pdfs`.
Instead of simply specifying the value, one can use a character to define an action, followed by the corresponding configuration:

    * `I` specifies a free parameter. Only one argument is required: its
    initial value. This is optional; if no action is specified the parameter is considered free.
    * `F` configures a fixed parameter. The following argument indicates
    at which value to fix it.
    * `L` is used for a limited parameter. Initial value, lower limit and
    upper limit follow.
    * `G` is used for a Gaussian-constrained parameter. The arguments of that
    Gaussian, ie, its mean and sigma, have to be given after the action.

This processing is performed by the `utils.config.configure_parameter`, which also returns any resulting constraints from the configuration.

In addition it is possible (and very recommended) to specify an `initial-yield` so the fitter can converge better.


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

