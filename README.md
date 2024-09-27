# µArchiFI

**µArchiFI** is a formal tool for analyzing the robustness of embedded systems against fault injection attacks by combining the RTL of a processor, the binary of a software, and an attacker model. µArchiFI takes into account the subtle interactions between the microarchitecture and the software running on the processor. µArchiFI can formally prove the security, for a given attacker model, of a system embedding countermeasures to fault injections. If not proven, µArchiFI can return counterexamples illustrating how fault injection can leverage vulnerabilities. 

µArchiFI uses the [Yosys](https://github.com/YosysHQ/yosys) open-source hardware synthesis environment to produce formal models of both the hardware and the software. These models are enriched with fault injection capabilities that can be controlled spatially, temporally and in terms of bit effects.

This repository contains the source code for the paper "*μArchiFI: Formal Modeling and Verification Strategies for Microarchitectural Fault Injections*" (see [Publication](#publication)). In theory, the output of the [k-Fault-Resistant Partitioning](https://github.com/CEA-LIST/Fault-Resistant-Partitioning) tool can be used as the input fault model of µArchiFI.


## TL;DR

```sh
# Build tool using Make
make build

# Add in your path the built yosys
export PATH=./build/yosys:$PATH

# To generate 2 formal models (BTOR and SMT-LIB) for a given use-case
cd usecases/1.robust_software/
make prep_baseline

# To evaluate one formal model  (BTOR)
make yosysmc
```

## Overview

The repository is structured as follows:
- `src`: Source code of the `FaultRTLIL` pass, which is added within the Yosys infrastructure for evaluating circuit robustness against fault injections.
- `usecases`: Case studies evaluated in the paper.

## Install and Build

µArchiFI clones a specific version of Yosys (0.25), adds the FaultRTLIL pass to it, and compiles Yosys. Everything is done using:
```
make build
```
Yosys is built in the `build/yosys` directory.

Other formal tools can be used, such as Pono, and verifications can be run using the following commands: `make pono`, `make btormc` For installing Pono, please refer to https://github.com/stanford-centaur/pono

## Usage

Within each use case, a Makefile is provided. See the README file associated to each use case for details.
- Use case I: Robust Software: [README.md](./1.robust_software/README.md)
- Use case II: Robust Hardware: [README.md](./2.robust_hardware/README.md)
- Use case III: Crypto Software: [README.md](./3.crypto_software/README.md)

Each use case includes scripts for Yosys to parse Verilog, simulate the design to reach a specific clock cycle, add fault injection points, and finally generate formal models. Please refer to the `script` directory for more details.

## Results Interpretations

Bounded model checking either proves the robustness (for a given fault model) at a specific verification step before incrementing it to reach the targeted bound:
```
# With Pono
[2024-09-23 11:54:11.955674] BMC checking at bound: 55
[2024-09-23 11:54:11.955683]   BMC reached_k = 54, i = 55 
[2024-09-23 11:54:11.955692]   BMC adding transition for j-1 = 54
[2024-09-23 11:54:11.979838]   BMC adding bad state constraint for j = 55
[2024-09-23 11:54:12.832495]   BMC check at bound 55 unsatisfiable

# With Yosys-smtbmc
[2024-09-23 16:09:18.644380] ##   0:02:30  Checking assumptions in step 69..
[2024-09-23 16:09:23.582891] ##   0:02:35  Checking assertions in step 69..
[2024-09-23 16:10:31.020274] ##   0:03:43  Checking assumptions in step 70..
[2024-09-23 16:10:36.504236] ##   0:03:48  Checking assertions in step 70..
```
or shows a counter-example found at a specific step. Different formats are possible depending on the verification tool being used:
```
# With Pono
[2024-09-23 11:55:09.533820] BMC checking at bound: 70
[2024-09-23 11:55:09.533829]   BMC reached_k = 69, i = 70 
[2024-09-23 11:55:09.533838]   BMC adding transition for j-1 = 69
[2024-09-23 11:55:09.567581]   BMC adding bad state constraint for j = 70
[2024-09-23 11:55:54.579887]   BMC check at bound 70 satisfiable
[2024-09-23 11:55:54.579976]   BMC saving reached_k_ = 69
[2024-09-23 11:55:54.579988]   BMC get cex upper bound: lower bound = 70, upper bound = 70 
[2024-09-23 11:55:54.580613]     BMC get cex upper bound, checking value of bad state constraint j = 70
[2024-09-23 11:55:54.580650]     BMC get cex upper bound, found at j = 70
[2024-09-23 11:55:54.580662]   BMC permanently blocking interval [start,end] = [71,70]
[2024-09-23 11:55:54.580672] 
[2024-09-23 11:55:54.580682]   BMC binary search, cex found in interval [reached_k+1,upper_bound] = [70,70]
[2024-09-23 11:55:54.580692]   BMC interval has length 1, skipping search for shortest cex
[2024-09-23 11:56:25.848295] sat
[2024-09-23 11:56:25.848421] b0
[2024-09-23 11:56:25.875069] #0
[2024-09-23 11:56:25.875191] 0 00000000000000000000000000000000 core_i.id_stage_i.alu_operand_a_ex_o@0
[2024-09-23 11:56:25.875206] 1 00000000000000000000000001010101 core_i.id_stage_i.alu_operand_b_ex_o@0
[2024-09-23 11:56:25.878498] 2 1 state223@0
[2024-09-23 11:56:25.882278] 3 0 state229@0
[2024-09-23 11:56:25.885516] 4 1 state250@0
[2024-09-23 11:56:25.888446] 5 0 state254@0
[2024-09-23 11:56:25.892911] 6 00 state257@0
[2024-09-23 11:56:25.892946] 7 00000000000000000000000000000000 core_i.id_stage_i.alu_operand_c_ex_o@0
[2024-09-23 11:56:25.893987] 8 00 state273@0
[2024-09-23 11:56:25.894016] 9 001 state302@0
[2024-09-23 11:56:25.894026] 10 1010 state309@0
[2024-09-23 11:56:25.894034] 11 0 state315@0
[2024-09-23 11:56:25.894042] 12 1010 state321@0
[2024-09-23 11:56:25.894050] 13 101 state328@0
[2024-09-23 11:56:25.894058] 14 1110 state335@0
[2024-09-23 11:56:25.894066] 15 1 state341@0
[2024-09-23 11:56:25.894074] 16 1101 state348@0
[2024-09-23 11:56:25.894082] 17 000 state355@0
[2024-09-23 11:56:25.894090] 18 0 state361@0
[2024-09-23 11:56:25.894097] 19 00 state367@0
[2024-09-23 11:56:25.894105] 20 0 state373@0
[2024-09-23 11:56:25.894113] 21 0 state379@0
[2024-09-23 11:56:25.894121] 22 0 state385@0
[2024-09-23 11:56:25.894129] 23 000000 state392@0
[2024-09-23 11:56:25.894137] 24 0 state398@0
...

# With Yosys-smtbmc (with a counter-example written in the VCD format)
[2024-09-23 16:10:36.504236] ##   0:03:48  Checking assertions in step 70..
[2024-09-23 16:11:36.475702] ##   0:04:48  BMC failed!
[2024-09-23 16:11:36.475775] ##   0:04:48  Assert failed in cv32e40p_wrapper: src/cv32e40p_verifypin_v7.v:9056.4-9074.3|src/cv32e40p_verifypin_v7.v:9142.85-9143.34|src/cv32e40p_verifypin_v7.v:9767.4-9781.3 ($flatten/ram_i./dp_ram_i.$assert$src/cv32e40p_verifypin_v7.v:9142$8010)
[2024-09-23 16:11:36.475788] ##   0:04:48  Writing trace to VCD file: .../uArchiFI/usecases/1.robust_software//out/counter_example.vcd
[2024-09-23 16:11:48.421869] ##   0:05:00  Status: FAILED
```

## Publication
Tollec, S., Asavoae, M., Couroussé, D., Heydemann, K., Jan, M. [μArchiFI: Formal Modeling and Verification Strategies for Microarchitectural Fault Injections](https://repositum.tuwien.at/handle/20.500.12708/188805). *Proc. 23rd Conference on Formal Methods in Computer-Aided Design – FMCAD 2023*, pp. 101–109.


## Licensing
Unless otherwise noted, everything in this repository is covered by the Apache License, Version 2.0 (see [LICENSE](./LICENSE.txt) for full text).

