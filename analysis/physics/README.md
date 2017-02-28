Physics
=======

Classes defining physics factories, used to generate PDFs.
The advantage of these factories is that they allow to instantiate PDFs from a configuration dictionary.

For each type of observable, which is defined analysis by analysis, a PDF can be defined, in the most general case, with:

```python
{'observables': name,
 'type': pdf_type,
 'parameters': {param1_name: param1_value,
                param2_name: param2_value}}
```

Where `name` can take any value of the keys of `PHYSICS_FACTORIES` global variable and `pdf_type` depends on each observable type (please see each module documentation for the defined PDFs).

Additionally, parameters can be renamed by giving passing a dictionary of `(param_name, param_new_name)` key-value pairs in the `parameter-names` key.
This is useful because most factories expect their parameters to have specific names (see the docs for each particular factory to see which names are required).

This configuration can be achieved through YAML files that can be loaded using the `analysis.utils.config.load_config` function.
The equivalent in YAML to the previous dictionary would be generate with:

```yaml
observables: name
type: pdf_type
parameters:
    param1_name: param1_value
    param2_name: param2_value
```

Factories are instantiated with the `analysis.get_physics_factory` function, which takes one or more of the above mentioned configurations.
If more than one is given, an uncorrelated product of observables will be built.

