---
title: "HEAT: High-Efficiency Simulation for Thermal Ablation Therapy"
description: "GPU-accelerated real-time thermal ablation simulation published in IJCARS 2025"
slug: 2025-heat-ijcars
date: 2025-04-01 00:00:00+0000
categories:
    - Research
tags:
    - Publication
    - Thermal Ablation
    - GPU Computing
    - Python
    - Medical Imaging
    - Simulation

---

## Abstract

Percutaneous thermal ablation is increasingly popular but still suffers from a complex preoperative planning, especially regarding the prediction of the ablation zone. We propose **HEAT** (High-Efficiency simulation for thermal Ablation Therapy), a novel GPU-accelerated simulation framework for thermal ablation that enables real-time planning.

This work was published in the *International Journal of Computer Assisted Radiology and Surgery (IJCARS)* in 2025.

[📄 Read the Paper](https://hal.science/hal-04973371) · [🔬 DOI](https://doi.org/10.1007/s11548-025-03350-z)

---

## Motivation

Thermal ablation is a minimally invasive cancer treatment that uses heat to destroy tumors. However, accurately predicting the ablation zone (the area that will be destroyed) remains challenging. Traditional simulation methods are too slow for clinical use, taking minutes or even hours to compute.

## Approach

HEAT leverages GPU acceleration to achieve real-time performance:

- **Fast computation**: Results in under 1 second for interactive planning
- **GPU parallelization**: Efficient handling of 3D volumetric data
- **Physical accuracy**: Implements realistic heat transfer models including:
  - Pennes bioheat equation
  - Perfusion effects
  - Heat sink effects near blood vessels

## Results

The system demonstrates:
- **Real-time performance**: Sub-second simulation times
- **Clinical accuracy**: Validated against experimental data
- **Practical utility**: Integrates with existing surgical planning workflows

## Authors

- **Jonas Mehtali** (Lead Author)
- Juan Verde
- Caroline Essert

*ICube Laboratory, University of Strasbourg*

## Related Work

This work builds on my research internship in 2024 at ICube/IHU Strasbourg, which focused on networked computing for thermal ablation simulation. The HEAT project represents a significant advancement in computational efficiency and clinical applicability.

See also: [Cryotrack: Planning and Navigation for Computer Assisted Cryoablation (MICCAI 2024)](/p/2024-cryotrack-miccai/)