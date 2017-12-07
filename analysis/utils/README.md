Utils
=====

This package contains several utilities used throughout the package.

config
------

Several helpers dealing with yaml configuration files are placed
inside.

- Loading (and interpreting substitutions) as well as dumping a configuration
can be achieved with `load_config` resp. `write_config`.

- Comparing two dictionaries and finding the differences is done by
`compare_configs`.

- In order to manipulate nested dicts easier, `unfold_config` resp.
`fold_config` convert the dicts to a file-like structure.

- The logic of converting a parameter specified in the configuration
into a ROOT object is implemented in `configure_parameter`.

- Adding shared variables is done with `get_shared_vars`.


decorators
----------

This module contains the decorators used throughout this library.

- `memoize` is memorizing the creation of a class if a function is called
with the same arguments again as before.


fit
---

Helpers for the fitting and results.

- `fit_parameters` converts fitted RooRealVars into a dict containing
information about the errors.

- `calculate_pulls` creates pulls taking no error/ the symmetric error/
asymmetric errors into account.


iterators
---------

Several iterators for large iterations are available.

- `pairwise` converts a sequence s -> (s0, s1), (s1, s2), (s2, s3)

- `chunks` iterator over chunks given a chunksize


logging_color
-------------

Logging related utils.

- To get a new logger given a certain name, use `get_logger`.


monitoring
----------

Functions to monitor the resources needed for execution.

Memory usage can be tracked with `memory_usage`.

Tracking the execution time can be achieved using the context manager of `Timer`.


path
----

The path management of the package happens inside this module.

Several default paths are set:

- toy
- toy config
- toy fit
- toy fit config
- log
- efficiency
- genlevel mc
- plot style
- fit result

- Additional paths can be added with `register_path`.

- To save a file, `prepare_path` takes care of the right naming, implicit
folder creation and more.
- If you want in addition to that to work with a
file in a thread-safe manner, the function (or better contextmanager)
`work_on_file` can be used.

 
pdf
---

TODO


random
------

Any randomness related utils.

- In order to retrieve a *really* random integer, use `get_urandom_int`.


root
----

ROOT framework related functions including iterators for ROOT containers.

- `load_library` is used to load a C++ library or to compile it inplace.

- `destruct_object` deletes ROOT objects safely.

- A functional helper is the `execute_and_return_self` function, which 
executes an object and returns it again.

#### Different Converters

The following converters are implemented:

- Python list to 
    - RooAbsCollection
    - RooArgList
    - RooArgSet

- RooArgSet to
    - Python set
- RooArgList to
    - Python list

The following iterators are implemented:

- To iterate over a RooAbsCollection, use `iterate_roocollection`

