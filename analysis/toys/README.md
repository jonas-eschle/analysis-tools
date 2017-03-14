Toys
====

Scripts for toy data generation and fitting.


Toy generation
--------------

The `generate_toys.py` script creates the toy datasets.
Its output is written into a `pandas.HDFStore` file, which contains two trees:

  - `data` contains a `pandas.DataFrame` with the generated events, as well as the ID of the job used to generate it (in case the script is run in standalone mode, this ID is 'local').
  - `toy_info` contains the information for each job: seed, number of events and values of the generation parameters.

This information should be enough to reconstruct any generation process. 

It's important to realize that the user has no control on the output locations, as these are all controlled by the `analysis.utils.paths` module.
Generated data are stored in the `analysis/data/toys/gen` folder, and the file name is `{name}.hdf`, where `name` is defined in the configuration file.

The only possibility for location configuration is the use of the `link-from` configuration, which actually builds the folder hierarchy in the specified folder (typically in a large storage space) and symlinks everything to the current one.

Toys are configured with YAML files, such as:

```yaml
name: Test
nevents: 23
folding: S4
pdfs:
    - observables: angular
      type: signal
      parameters:
          - S4: 1.0
    - observables: mass
      type: doublecb
    - observables: q2
      type: flat
```

The `pdfs` key configures the generation PDFs, and details on how to configure them can be found in [the physics README](../physics/README.md).
**Note**: Parameter renaming is ignored in this case to help with portability.

Toy production is a highly parallel job, and to allow this the `submit_generate_toys.py` script is provided.
This script is configured with the same YAML files as the single toy script, with the extra mandatory key `nevents-per-job`, which specifies the number of events produced per job (`nevents` controls the *total* amount of toys produced).
Additionally, the `runtime` key, written in the `HH:MM:SS` format, allows to control cluster execution (defaults to `08:00:00`).

Whenever a configuration file is used in `submit_generate_toys.py`, it is copied to the same folder as the `.hdf` file with the `.yml` extension.
This allows to keep track of all productions in a sustainable way, since toys will not be overridden unless explicitly stated when executing the script.

### Trick

If using the `link-from` option, several users can share the same toys if the config file is committed (or we know its location) and the same `link-from` is given.
When executin `submit_generate_toys.py`, it checks for the existence of the toy file.
If it does, it is simply symlinked to the user directory, thus making everything work.


Toy fitting
-----------

The `fit_toys.py` script fits the data.
Its output is written into a `pandas.HDFStore` file containing two trees:

  - `fit_{model_name}` contains the final value and errors, toy by toy, of each fit parameter, for model `model_name`.
  Since `pandas` doesn't happily support objects with uncertainties, for each parameter `par` we store 4 columns:
  `{par}` is the parameter value, `{par}_err_hesse` contains the Hessian error (from `RooFit`'s `getError`), and `{par}_err_plus` and `{par}_err_minus` contain the asymmetric Minos errors.
  Additionally, the per-toy pulls are also computed, and saved as `{par}_pull_hesse` and `{par}_pull_minos`.
  - `gen_info` contains the information of the input datasets used to extract the fit input data.

As before, the user has no control on the output location, as these are all controlled by the `analysis.utils.paths` module.
Generated data are stored in the `analysis/data/toys/fit` folder, and the file name is `{name}.hdf`, where `name` is defined in the configuration file.
As before, `link-from` can also be used.

Fits are configured with YAML files, such as:

```yaml
name: SignalFit
fit:
    nfits: 10
    minos: yes
    models:
        - model
    strategies:
        - simple
model:
    signal:
        initial-yield: 989
        pdfs:
            - observables: angular
              type: signal
              folding: S4
data:
    signal:
      source: SignalTest
      nevents: 1000
```

The `fit` key configures the fit work, setting the total number of samples to be taken and the fit configuration (currently only `minos` is supported).

The `model` key configures the fit model by default.
However, several different fit models (for the same dataset) can be specified with the `fit/models` keys;
in this case, the names specified in such key are used to search for models.
In it, one can add as many PDFs as needed, with the key being their name.
Each of these PDFs is defined the same way as in the generation case (that is, using the `pdfs` entry), and in addition it is possible (and very recommended) to specify an `initial-yield` so the fitter can converge better.
In the end, all objects specified in the `model` dictionary are added using a `RooAddPdf` after converting each PDF into an `RooExtendPdf`.

Similarly, several fit strategies can be specified with the `fit/strategies` key.
A basic one (`model.fitTo`) is implemented with the name `simple`, but more can be registered by adding them to the `FIT_STRATEGIES` global variable dictionary.
These fit strategies should consist of a function that gets the model (PDF), the dataset to fit and the fit options, and return a `RooFitResult`.

The `data` key is used to specify the input data for each toy.
Each of the entries is used to load a toy generated by `generate_toys.py` using its name (`source`), and configures the number of entries to sample from the input data set (`nevents`).
Note that the number of events will be Poisson-fluctuated since the fit is always extended.
In the end, all sampled datasets are merged and used as the data for the fit.

