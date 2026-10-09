---
contribution: "First author"
authors: "Jonas Mehtali, Juan Manuel Verde, Caroline Essert"
title: "C-NCA: Chained Neural Cellular Automata for Fast and Accurate Thermal Ablation Estimation"
description: "A learned model for estimating tissue damage in radiofrequency ablation, trained and evaluated against numerical simulations."
slug: cnca-2025
aliases: ["/p/cnca-2025/"]
date: 2025-09-22 00:00:00+0000
image: TargetOutput.png
categories:
    - Research
tags:
    - Publication
    - MICCAI
venue: "MICCAI 2025 · Seoul"
tldr: "Chained neural cellular automata that estimate thermal tissue damage from simulated ablation plans."
doi: "10.1007/978-3-032-04965-0_7"
paper: "https://papers.miccai.org/miccai-2025/paper/4370_paper.pdf"

links:
- title: "E-Poster"
  description: "E-Poster presented at MICCAI 2025"
  website: cnca-e-poster.pdf
- title: "Publisher chapter"
  description: "Springer LNCS — full text"
  website: "https://link.springer.com/chapter/10.1007/978-3-032-04965-0_7"

---

## Overview

C-NCA uses chained neural cellular automata to estimate tissue damage from radiofrequency ablation plans. The model learns from numerical simulations, with the aim of reducing the computation needed to compare needle placements.

**Authors:** Jonas Mehtali, Juan Manuel Verde and Caroline Essert. Published at MICCAI 2025.

## Evaluation

The published study evaluates predictions against a finite-difference simulation. On an RTX 4080 SUPER, the 4 mm model averaged 2.1 ms per prediction (476 fps), with 1.74% average RMSE against the reference. These are simulation-benchmark results for the reported configuration, rather than patient outcome measurements.

[Read the open-access paper](https://papers.miccai.org/miccai-2025/paper/4370_paper.pdf) · [Publisher record](https://doi.org/10.1007/978-3-032-04965-0_7)

## Figures

{{< figure src="prediction_pipeline.png" title="C-NCA prediction pipeline" >}}
{{< figure src="TargetOutput.png" title="Reference simulations and model predictions" >}}

## BibTeX

```bibtex
@inproceedings{mehtali2025cnca,
  title     = {C-NCA: Chained Neural Cellular Automata for Fast and Accurate Thermal Ablation Estimation},
  author    = {Mehtali, Jonas and Verde, Juan Manuel and Essert, Caroline},
  booktitle = {Medical Image Computing and Computer Assisted Intervention -- MICCAI 2025},
  year      = {2025},
  publisher = {Springer},
  doi       = {10.1007/978-3-032-04965-0_7}
}
```
