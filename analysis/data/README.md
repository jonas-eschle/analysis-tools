# Data management (`analysis.data`)

Two basic functions are provided to load datasets (ROOT or `pandas`) in a fast an efficient way: `load_data` and `get_data`.
Both can be imported from the `analysis.data` module and follow the same naming conventions as other modules in the package:
the `get_data` function loads a dataset from a configuration dictionary, while the `load_data` does the same by loading the configuration dictionary from a YAML file.

Other than this difference, both functions follow the same configuration (see their `help` for the details on which arguments to pass to them).
The required configuration keys are:

  + `source`: Input source.
  If `source-type` is specified, the file name will be obtained executing `get_{source-type}_path`, otherwise `source` is treated as a file name.
  
  + `tree`: Tree (or `HDF` key) within the file.
  
  + `output-format`: Type of data we want to be returned by the function.
    Currently `root` or `pandas` are accepted.

For this to work, the file extension needs no have been registered (currently `root`, `h5` and `hdf` are registered).
If you use a different file extension, you need to specify the `input-type` to be either `root` or `pandas`.

On top of this, several options can be specified to load the data, depending on the input and output types:

  + `variables` is a list of the variables to be loaded into the data set.
  If not specified, all variables from the input are loaded.

  + A list of weight variables can be specified using the `weights-to-normalize` and `weights-not-normalized` entries.
  A product these variables will be used as weight, with its name chosen according to the following rule:
  if only one variable is specified, its name will be used as the name of the weight variable;
  otherwise, `weight-var-name` needs to be specified to give name to the product variable.
  The product is done in the following way:

    1. The variables specified in `weights-to-normalize` are multiplied and the resulting combined weight is normalized
    to the total number of entries.
    2. The variables in `weights-not-normalized` are then multiplied to the previously normalized weight variable, and 
    the result is the final weight.

  + The `selection` string allows to specify a pre-selection on the dataset.
  The syntax is dependent on the input, that is, for ROOT files the usual `TCut` syntax is used, while for Pandas objects the syntax of `HDFStore.query` is used.

**Only** for ROOT output, `name` and `title` **must** be specified to configure the `RooDataSet` object.
Additionally, the `categories` list can contain the list of variable names to use as categories;
if several categories are given, a `RooSuperCategory` is built, and its name is the names of each category joined by `x` characters.
(**Note:** currently categories are not implemented when loading ROOT files to the ROOT output).

**Only** for `pandas` input (for the moment), an acceptance can be loaded using the `acceptance` entry, which is configured as any acceptance object.
This needs to be accompanied with a weight specification, either in `weights-to-normalize` or `weights-not-normalized`;
this specification is either `acceptance_fit` or `acceptance_gen`.
Depending on which one is specified, `acceptance.get_fit_weights` or `acceptance.get_gen_weights` is used.
