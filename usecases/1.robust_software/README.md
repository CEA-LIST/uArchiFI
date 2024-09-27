# Use case I: Robust Software

## Use case Scenario

Use Case I illustrates the analysis of a secure program running on a processor.
The considered software is VerifyPIN v7 from the [FISSC benchmark suite](https://lazart.gricad-pages.univ-grenoble-alpes.fr/fissc/).
The hardware is the CV32E40P core from the [OpenHardware Group](https://github.com/openhwgroup/cv32e40p).
The attacker aims to bypass the secure authentication mechanism without triggering the software countermeasures.
The fault model is a single fault injection on the sequential logic of the processor control path during the status comparison.

## Use case Structure

- **src**: contains the hardware and the software description
- **script**: contains the Yosys scripts to automatically build the formal model 
- **out**: contains output files
- **Makefile**: Makefile targets to build the model and run the verifications
- **README.md**: this file

## Run instructions

### Baseline Verification
To generate the formal model for the base case, run `make prep_baseline`.<br/>
To run the bounded model checking, run `make <tool>` with tool = {yosysmc | pono | btormc}.

### Sandboxing Verification
To generate the formal model for the base case, run `make prep_sandboxing`.<br/>
To run the bounded model checking, run `make <tool>` with tool = {yosysmc | pono | btormc}.
