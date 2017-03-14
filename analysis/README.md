Analysis tools
==============

Currently, this framework basically supports toys.
Configuration of toys (generation, submission) is done with the modules in the `toys` folder.
The `physics` folder can be used to implement the physics factories used for the toys (see [its README](physics/README.md)).
The `utils` folder contains many useful modules and functions, discussed in [its README](utils/README.md).
Common PDF code can be found in the `pdf` folder.

The configuration of the module is controlled through a global dictionary that contains the following keys:

  - `BASE_PATH`: The root path of the analysis module.
  - `PDF_PATHS`: Search path for PDF code.
  - `PHYSICS_FACTORIES`: Physics observables and PDFs. It is blank in this module, so it needs to be overwritten by each specific analysis.
  - `FIT_STRATEGIES`: Fit strategies implemented for the given analysis.

To implement an analysis based on `analysis tools`, the user needs to implement their own physics models and load them in the global dictionary.
Additionally, the base path can be modified to suit the user's needs.