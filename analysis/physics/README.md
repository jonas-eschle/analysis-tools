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


## Configuring physics factories

Physics factories can be loaded and configured using the `analysis.physics.configure_fit_factory` function, which takes a name and a dictionary (easily taken from a YAML file).
The `pdfs` key is used to load the `PhysicsFactory` in the same way as `get_physics_factory`, but additional constraints can be imposed on the parameters.
Instead of simply specifying their value, one can use strings, which we will call `RooVarConfig` in the following, to define more complex variable configurations (details can be found below). 
This processing is performed by the `utils.config.configure_parameter`, which also returns any resulting constraints from the configuration.

On top of this, all parameters are renamed according to the name given to the factory with the template `{param_name}^{factory_name}`.
This will allow to differentiate them when adding several `PhysicsFactory` instances to make a fit model.
In this way, the factory and its parameters are properly configured, and any constraints derived from their configuration are obtained.


### Normal variables

Mimicking `ROOT.RooRealVar`, one can defined three types of variables:
floating (bound and unbound), constant and constrained.


#### Floating variable

The floating variable can be either bound or unbound, depending whether we specify limits or not.
The optional parameters are marked below in parenthesis:
of they are not given, the variable is unbound.

  + **ROOT analogue**: `ROOT.RooRealVar` with `setConstant(False)`.
  + **Specification**: VAR initial_val (minimum maximum)  
  + **Types**: string numerical (numerical numerical)  
  + **Example**: `VAR 500 450 570`  

Since this is the most used variable type, we can also simply specify `value` and the parameter configurator will interpret it as `VAR value`.


#### Constant variable

A numerical constant.

  + **ROOT analogue**: `ROOT.RooRealVar` with `setConstant(True)`  
  + **Specification**: CONST value
  + **Types**: string numerical  
  + **Example**: `CONST 13.41`  


#### Constrained variable

Currently implemented is the Gaussian constraint of a parameter.

  + **ROOT analogue**: `ROOT.RooRealVar` with a `ROOT.RooGaussian` constraint  
  + **Types**: string numerical numerical  
  + **Specification**: GAUSS gaussian_mu gaussian_sigma
  + **Example**: `GAUSS 647 15`  

This configures a `ROOT.RooRealVar` and creates a `ROOT.RooGaussian` constraint to be used during fitting.


### Shift, scale and blind

These options are used to configure the parameter as a modification of another value already defined.
It is therefore necessary to "refer" to another variable, and this means using a *shared variable* (explained below) for this referenced value.


#### Shift variable

Define a variable as a linear shift with respect to another variable.
The shift value can be defined as any of the other types of variables define above.

  + **ROOT analogue**: `ROOT.RooAddition`  
  + **Specification**: SHIFT variable_to_shift_from shift_value    
  + **Types**: string reference RooVarConfig     
  + **Example**: `SHIFT @muTrue VAR 500 200 900`  


#### Scale variable

Define a variable as a scale with respect to another variable.

  + **ROOT analogue**: `ROOT.RooProduct`  
  + **Specification**: SCALE variable_to_be_scaled scale_value
  + **Types**: string reference RooVarConfig  
  + **Example**: `SCALE @sigma1 VAR 3 1 5`  


### Blinding

Parameter blinding is performed with `ROOT.RooUnblindPrecision`, so a string, a central value and a sigma value need to be provided.

  + **ROOT analogue**: `ROOT.RooUnblindPrecision`
  + **Specification**: BLIND blinding_reference blind_str central_val sigma_val  
  + **Types**: string reference  string numerical numerical  
  + **Example**: `BLIND @sigma1 uzhirchel 15 36`  

*Hint*: to blind a region of a given observable, you can use the `selection` parameter to cut it off at load time and a custom fit strategy to fit the disjoint fit range.


### Shared variables

Shared variables are normal variables that can be referenced after they have been defined, by using the syntax `@ref_name`.

  + **Specification**: @reference_name/variable_name/variable_title/variable_config
  + **Types**: @string/string/string/RooVarConfig
  + **Example**: `@mu1_low/mu1/mu_the_lower/VAR 50 10 90` (shared free floating variable) 
 
The two main types of usage are:  
  + Just the reference: `@mu1_low`  
  + Within another variable: `SHIFT @mu1_low 2701` (shift the value 2071 by @mu1_low)    


### Loading from other files

To load values from fit results (or any other configuration file), numerical values can be replaced by:

	+ `file_name:key` loads file `file_name` and takes the value of `key` from it (`key` has the `key\subkey` syntax).
	+ `path_func:name:key format` uses `get_{path_func}_path({name})` to get the file name, and then works like in the previous case.

Whole sections of config files can be loaded using the `load` and `modify` syntax.
To load a certain section of a `YAML` file, put a `load` keyword where the loaded part should be attached, giving as value the path of the file to load and the key to load, separated by a colon.
The `modify` keyword can be used to then modify the loaded values:
simply give the path of the key you want to modify and its new value.

For example, we create a `base_model.yaml` file as follows:

```yaml
pdf:
    sig:
        parameters:
            mu: CONST 5.0
            sigma: CONST 36.2
            alpha: CONST -0.43
    bkg:
        parameters:
            lambda: CONST 3.2
```

Then, we can use it as base of a more complex configuration file:

```yaml
pdf:
    sig:
        load: base_model.yaml:parameters
        modify:
            parameters:
                alpha: CONST 0.54
    other_sig:
        parameters:
            mu: CONST 2.3
            sigma: CONST 151
```

which will result in the *effective* configuration:

```yaml
pdf:
    sig:
        parameters:
            mu: CONST 5.0
            sigma: CONST 36.2
                alpha: CONST 0.54
    other_sig:
        parameters:
            mu: CONST 2.3
            sigma: CONST 151
```

Alternatively, the `modify` keys can be specified as paths, *e.g.*,`parameters/alpha: CONST 0.54` could be used instead of

```yaml
parameters:
    alpha: CONST 0.54
```

*Note that not using `modify` in order to alter a loaded configuration will raise an error!*.
This example will fail (by design):

```yaml
pdf:
    sig:
        load: path/to/file/result.yaml:parameters
        parameters:
            alpha: CONST 0.54
```
