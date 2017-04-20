Physics
=======

Classes defining physics factories, used to generate PDFs.
The advantage of these factories is that they allow to instantiate PDFs from a configuration dictionary.

For each type of observable, which is defined analysis by analysis and stored as a key in the `PHYSICS_FACTORIES` global variable, a PDF can be defined, in the most general case, with:

```python
{'pdf': pdf_type,
 'parameters': {param1_name: param1_value,
                param2_name: param2_value}}
```

Where `pdf_type` depends on each observable type (please see each module documentation for the defined PDFs).

Additionally, parameters can be renamed by giving passing a dictionary of `(param_name, param_new_name)` key-value pairs in the `parameter-names` key.
This is useful because most factories expect their parameters to have specific names (see the docs for each particular factory to see which names are required).

This configuration can be achieved through YAML files that can be loaded using the `analysis.utils.config.load_config` function.
The equivalent in YAML to the previous dictionary would be generate with:

```yaml
obs_type:
   pdf: pdf_type
   parameters:
       param1_name: param1_value
       param2_name: param2_value
```

Factories are instantiated with the `analysis.physics.get_physics_factory` function, which takes one or more of the above mentioned configurations.
If more than one is given, an uncorrelated product of observables will be built.


Configuring physics factories
-----------------------------

Physics factories can be loaded and configured using the `analysis.physics.configure_fit_factory` function, which takes a name and a dictionary (easily taken from a YAML file).
The `pdfs` key is used to load the `PhysicsFactory` in the same way as `get_physics_factory`, but additional constraints can be imposed on the parameters.
Instead of simply specifying their value, one can use a character to define an action, followed by the corresponding configuration:

    * `I` specifies a free parameter. Only one argument is required: its initial value. This is optional; if no action is specified the parameter is considered free.
    * `F` configures a fixed parameter. The following argument indicates at which value to fix it.
    * `L` is used for a limited parameter. Initial value, lower limit and upper limit follow.
    * `G` is used for a Gaussian-constrained parameter. The arguments of that Gaussian, *i.e.*, its mean and sigma, have to be given after the action.

This processing is performed by the `utils.config.configure_parameter`, which also returns any resulting constraints from the configuration.

On top of this, all parameters are renamed according to the name given to the factory with the template `{param_name}^{factory_name}`.
This will allow to differentiate them when adding several `PhysicsFactory` instances to make a fit model.
In this way, the factory and its parameters are properly configured, and any constraints derived from their configuration are obtained.


