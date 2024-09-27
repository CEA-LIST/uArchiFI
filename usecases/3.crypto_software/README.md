# Use case III: Crypto Software

## Use case Scenario

Use Case III illustrates the analysis of a software implementation of a cryptographic algorithm.
For instance, this analysis can be used as a basis to perform differential fault analysis.
The considered software is the [tiny AES](https://github.com/kokke/tiny-AES-c).
The hardware is the Ibex core from [LowRISC](https://github.com/lowRISC/ibex).
The attacker aims to set a small part of the key to zero during the last round of the key schedule algorithm by injecting up to two fault resets in the Execute stage of the processor.

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
