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

The description of the different variables and their syntax can be found below.

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


Variables
---------

RooVarConfig: configurations for the variables, like  
"CONST 5.9"  
or  
"VAR 4 3 5.6"

###Variable, constant and constraint


These are the more basic values.

#####Variable
The variable used for everything that is floating. Parameters have the same order as the
ROOT internally used Class (except that an initial value *has to be* provided).

ROOT analogue: RooRealVar (with min, max specified)  
Types: string numerical numerical numerical  
Meaning: VAR initial_val minimum maximum  
Example: VAR 500 450 570  

#####Constant
A numerical constant.

ROOT analogue: RooRealVar (without min, max specified)  
Types: string numerical  
Meaning: CONST value  
Example: CONST 13.41  


#####Constraint

Currently implemented is the gaussian constraining of a parameter.

ROOT analogue: ROOT.RooGaussian  
Types: string numerical numerical  
Meaning: GAUSS value("mean") value_error("sigma")  
Example: GAUSS 647 15  

###Shift, scale and blind

Those values have one thing in common: they "refer" to another value in one or the other way.
With the current implementation, it is necessary to use a *shared variable*
for this referenced value.

#####Shifting

ROOT analogue: RooAddition  
Types: string reference RooVarConfig     
Meaning: SHIFT variable_to_shift_from shift_itself    
Example: SHIFT @muTrue VAR 500 200 900  

#####Scaling

ROOT analogue: RooProduct  
Types: string reference RooVarConfig  
Meaning: SCALE variable_to_be_scaled scale_itself    
Example: SCALE @sigma1 VAR 3 1 5  

#####Blinding
For the blinding, a blind string is provided for the randomization, a central value
as well as a sigma value. Those three parameters are used to "blind" the parameter.

ROOT analogue: RooUnblindPrecision  
Types: string reference  string numerical numerical  
Meaning: BLIND blinding_reference blind_str central_val sigma_val  
Example: BLIND @sigma1 uzhirchel 15 36  



###shared variables

Shared variables can be referenced by their *reference_name*. Every variable can
be shared (so not strings, numerical etc. where sharing would not serve any purpose either).


Types: @string/string/string/string *(followed by params as needed for Roo variable config)*    
Meaning: @reference_name/variable_name/variable_title/type (type is the exact config
syntax for a variable)  
Example: @mu1_low/mu1/mu_the_lower/VAR 50 10 90 (shared variable of type VAR) 
 
Usage examples:  
just the reference: @mu1_low  
within another variable: SHIFT @mu1_low 2701 (shift the value 2071 by @mu1_low)    
