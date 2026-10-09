---
contribution: "First author"
authors: "Jonas Mehtali, Juan Verde, Caroline Essert"
title: "HEAT: High-Efficiency Simulation for Thermal Ablation Therapy"
description: "GPU-based thermal simulation with multiple resolutions for interactive needle planning."
slug: 2025-heat-ijcars
aliases: ["/p/2025-heat-ijcars/"]
date: "2025-04-10T00:00:00Z"
image: heat_sim_color.png
categories:
    - Research
tags:
    - Publication
    - Thermal Ablation
    - GPU Computing
    - Python
    - Medical Imaging
    - Simulation
venue: "IJCARS 2025"
tldr: "A multi-resolution GPU simulation that balances response time and detail while adjusting needle positions."
doi: "10.1007/s11548-025-03350-z"
paper: "https://hal.science/hal-04973371"
hal: "https://hal.science/hal-04973371"
---

## Overview

HEAT is a GPU-based simulation method for interactive thermal ablation planning. It uses a coarser estimate while the user adjusts needle positions, then computes a more detailed result when those positions are fixed.

The method compares finite-difference and lattice Boltzmann implementations of the Pennes bioheat equation.

**Authors:** Jonas Mehtali, Juan Verde and Caroline Essert. Published in *International Journal of Computer Assisted Radiology and Surgery*, 2025.

## Evaluation

The paper evaluates radiofrequency ablation scenarios against a reference simulation. It reports up to 5.8 fps for high-resolution frames and 32 fps for intermediate, lower-resolution frames. The latter trades some accuracy for responsiveness; the paper details that trade-off and the tested parameters.

[Read the author manuscript on HAL](https://hal.science/hal-04973371) · [Publisher record and abstract](https://doi.org/10.1007/s11548-025-03350-z)

## Related work

The project builds on my [2024 research internship](/pro/research/2024-assisted-surgery-internship/). [C-NCA](/pro/research/cnca-2025/) subsequently explored a learned estimator for thermal tissue damage.

## BibTeX

```bibtex
@article{mehtali2025heat,
  title     = {HEAT: High-Efficiency Simulation for Thermal Ablation Therapy},
  author    = {Mehtali, Jonas and Verde, Juan and Essert, Caroline},
  journal   = {International Journal of Computer Assisted Radiology and Surgery},
  year      = {2025},
  doi       = {10.1007/s11548-025-03350-z}
}
```
