# Chip-Hexa
Experimental 16-core processor architecture exploring hexagonal interconnects, energy efficiency, and performance-per-cost optimization.
# LUNZ HEX-16

### Experimental Open Processor Architecture

**LUNZ HEX-16 is an experimental processor architecture exploring the balance between multicore performance, energy efficiency, interconnect design, and implementation cost.**

The project investigates whether a simple 16-core processor connected through a hexagonal network can provide an attractive performance-per-watt and performance-per-cost trade-off.

This is an early-stage research project. Its design choices, simulation models, and performance hypotheses remain under development and require further validation.

## Project Vision

The goal is to develop an open, modular processor architecture that prioritizes efficiency and simplicity rather than maximizing hardware complexity.

The central research question is:

> Can a carefully balanced 16-core architecture achieve useful performance with lower energy consumption and implementation cost, without relying on large specialized accelerators?

The project focuses on the processor as a complete system: execution cores, caches, communication network, memory hierarchy, and power management.

## Initial Architecture

| Component                       | Initial design target                                          |
| ------------------------------- | -------------------------------------------------------------- |
| Processor cores                 | 16 homogeneous cores                                           |
| Execution model                 | In-order                                                       |
| Register width                  | 64 bits                                                        |
| Nominal clock target            | 3 GHz                                                          |
| Clock control                   | Configurable operating frequency                               |
| Interconnect                    | Hexagonal network-on-chip concept                              |
| L1 instruction cache            | 16 KiB per core, with a 14 KiB alternative under investigation |
| L1 data cache                   | 16 KiB per core, with a 14 KiB alternative under investigation |
| L2 cache                        | 2 MiB distributed-cache target                                 |
| Specialized AI/GPU accelerators | Not included in the initial design                             |
| Architecture status             | Pre-silicon research and simulation                            |

These values describe the current design baseline, not a fabricated or physically validated processor.

## Design Principles

### 1. Balanced Multicore Design

The architecture uses 16 relatively simple cores instead of depending on a single extremely complex core.

The intended benefit is to exploit parallelism while controlling hardware complexity, energy consumption, and implementation area.

### 2. Hexagonal Interconnect Research

The project investigates a hexagonal neighborhood structure for communication between processing tiles.

The network is intended to reduce unnecessary communication overhead and provide scalable local connectivity.

Actual benefits depend on routing, congestion, link width, physical placement, and workload behavior. They must be measured rather than assumed.

### 3. Energy-Aware Operation

The target operating frequency is 3 GHz, with configurable frequency operation as a design objective.

Future implementation work will investigate clock gating, idle states, and voltage/frequency management.

### 4. Cache and Memory Optimization

The project evaluates alternative cache capacities, including 14 KiB and 16 KiB L1 configurations.

The objective is to determine whether a smaller cache offers meaningful area and energy savings without excessive cache misses or additional control complexity.

### 5. Simplicity and Cost Awareness

Specialized accelerators and unnecessarily complex execution mechanisms are excluded from the initial baseline.

Hardware features will be considered when measurements demonstrate that their benefits justify their area, energy, and verification costs.

## Current Development Stage

The project currently includes an initial architectural specification and a Python-based simulation model.

Current research activities include:

* Exploring the 16-core hexagonal topology.
* Comparing cache-capacity alternatives.
* Evaluating configurable clock frequencies.
* Estimating throughput, execution time, and energy under synthetic workloads.
* Improving the simulator and defining reproducible tests.
* Preparing the architecture for future RTL implementation.

## Important Limitations

**The current results are simulation estimates, not measurements from physical silicon.**

The project has not yet demonstrated:

* A fabricated processor or a verified FPGA implementation.
* Performance superiority over x86, ARM, RISC-V, or commercial processors.
* Lower manufacturing cost than existing alternatives.
* Physical power consumption at 3 GHz.
* Validated area, timing, or power estimates from a synthesized hardware design.

Simulator results depend on the assumptions and parameters of the model. They must not be interpreted as directly comparable commercial benchmarks.

## Roadmap

1. Refine the architectural specification.
2. Improve the simulator's memory, cache, and network-contention models.
3. Define the instruction set and binary encoding.
4. Implement and test a single processor core in SystemVerilog.
5. Develop the network-on-chip and multicore memory-coherence system.
6. Verify functionality and evaluate area, timing, and power through appropriate hardware-design tools.
7. Explore FPGA prototyping and, eventually, ASIC implementation.

## Open Research

The project is intended to support reproducible experimentation, documentation, and future contributions.

Architecture decisions will be revised as new evidence becomes available. Performance, power, and cost claims will be documented together with the assumptions and methodology used to obtain them.

## Project Status

**Early-stage experimental architecture — pre-silicon.**

The LUNZ HEX-16 is a research effort toward a potentially efficient and cost-conscious multicore processor. Its proposed advantages remain hypotheses to be evaluated through simulation, RTL verification, synthesis, and physical implementation.

Contributions, technical criticism, and reproducible experiments are welcome.

## License

The hardware design, simulator, and documentation licenses will be explicitly identified in the repository. See the applicable license files before reusing or redistributing project materials.
