---
title: "Cryotrack: Planning and Navigation for Computer Assisted Cryoablation"
description: "Published at MICCAI 2024 - A novel planning and navigation system for cryoablation"
slug: 2024-cryotrack-miccai
date: 2024-10-06 00:00:00+0000
categories:
    - Research
tags:
    - Publication
    - MICCAI
    - Cryoablation
    - Navigation
    - Medical Imaging
    - Python

---

## Abstract

Cryoablation is a minimally invasive technique that uses extreme cold to destroy cancerous tumors. However, it remains challenging to plan and navigate during the procedure. We present **Cryotrack**, a novel planning and navigation system for computer-assisted cryoablation.

This work was published at the *27th International Conference on Medical Image Computing and Computer Assisted Intervention (MICCAI 2024)*, Marrakesh, Morocco, October 6-10, 2024.

[📄 Read the Paper](https://papers.miccai.org/miccai-2024/179-Paper1240.html) · [🔬 DOI](https://doi.org/10.1007/978-3-031-72089-5_10)

---

## Motivation

Cryoablation offers several advantages over thermal ablation:
- Precise control of the ablation zone
- Minimal pain for the patient
- Ability to treat tumors near sensitive structures

However, planning cryoablation procedures remains challenging due to:
- Complex ice ball formation dynamics
- Difficulty in visualizing the ablation zone in real-time
- Lack of dedicated planning tools

## Cryotrack System

Cryotrack provides:

1. **Pre-operative Planning**
   - 3D visualization of the target tumor
   - Simulation of ice ball growth
   - Optimization of probe placement

2. **Intra-operative Navigation**
   - Real-time tracking of cryoprobes
   - Augmented reality overlay of predicted ablation zone
   - Integration with imaging systems

3. **Visualization**
   - Clear visualization of the lethal ice zone vs. the benign cold zone
   - Heat sink effect awareness near blood vessels

## Results

The system was validated through:
- Phantom experiments
- Ex-vivo tissue testing
- Clinical feasibility studies

## Authors

- Henry J. Krumb
- **Jonas Mehtali**
- Juan Verde
- Anirban Mukhopadhyay
- Caroline Essert

*ICube Laboratory, University of Strasbourg*

## Conference Experience

Presenting at MICCAI 2024 in Marrakesh was an incredible experience. The feedback from the medical imaging community helped refine our approach and identify new research directions.

## Related Work

This work complements my later research on thermal ablation:
- [HEAT: High-Efficiency Simulation for Thermal Ablation Therapy (IJCARS 2025)](/p/2025-heat-ijcars/)