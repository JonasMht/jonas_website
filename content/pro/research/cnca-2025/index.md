---
title: "C-NCA : Chained Neural Cellular Automata"
description: "Fast thermal-ablation death estimation with chained neural cellular automata — 12,210 parameters, 476 fps."
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
tldr: "476 fps ablation-death estimation with 12,210 parameters — fast enough to plan inside the surgical loop."
doi: "10.1007/978-3-032-04965-0_7"
paper: "https://link.springer.com/chapter/10.1007/978-3-032-04965-0_7"

links:
- title: "E-Poster"
  description: "E-Poster presented at MICCAI 2025"
  website: cnca-e-poster.pdf
- title: "Publisher chapter"
  description: "Springer LNCS — full text"
  website: "https://link.springer.com/chapter/10.1007/978-3-032-04965-0_7"

---

## Description
We introduced an approach to estimate the heat induced tissue death in percutaneous thermal ablation based on a chained NCA architecture. While not directly producing a heat map, it accurately estimates cell death induced by thermal damage by implicitly modeling temperature field effects and evolution, going beyond heat distribution, with <b>low root mean square error and high speed</b>. The model is <b>computationally efficient</b>, characterized by a mere <b>12,210 learned parameters</b>, and is capable of operating on a standard desktop computer due to its implementation through basic 3D convolutions. It can compute 25 minutes of treatment at a frequency up to <b>476 fps</b>, making it suitable for interactive simulations and optimization loops.

## BibTeX
```bibtex
@inproceedings{mehtali2025cnca,
  title     = {C-NCA: Chained Neural Cellular Automata for Fast Thermal Ablation Estimation},
  author    = {Mehtali, Jonas and others},
  booktitle = {Medical Image Computing and Computer Assisted Intervention -- MICCAI 2025},
  year      = {2025},
  publisher = {Springer},
  doi       = {10.1007/978-3-032-04965-0_7}
}
```

{{< figure src="prediction_pipeline.png" title="Model Architecture" >}}
{{< figure src="TargetOutput.png" title="Target Output Pairs" >}}

{{< figure src="miccai2025-logo.png" width=50% alt="MICCAI 2025 Logo" >}}
{{< figure src="Planchette Logos.png" width=100% alt="Logos of collaborating institutions" >}}
