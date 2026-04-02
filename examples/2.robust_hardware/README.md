# Use case II: Robust Hardware

## Use case Scenario

Use Case II illustrates the analysis of a program running on a secure processor.
The considered software is VerifyPIN v1 from the [FISSC benchmark suite](https://lazart.gricad-pages.univ-grenoble-alpes.fr/fissc/).
The hardware is the Secure Ibex core from [LowRISC](https://github.com/lowRISC/ibex).
The processor implements protections against physical attacks like the redundancy-based Lockstep mechanism that instantiates the core twice and compares the outputs.
The attacker aims to bypass the secure authentication mechanism without triggering the hardware countermeasures.
The fault model injects up to four faults in the sequential logic duplicated core.

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
