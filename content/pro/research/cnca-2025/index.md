---
title: "C-NCA : Chained Neural Cellular Automata"
description: "Fast thermal-ablation death estimation with chained neural cellular automata, 12,210 parameters, 476 fps."
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
tldr: "476 fps ablation-death estimation with 12,210 parameters, fast enough to plan inside the surgical loop."
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
We estimate heat-induced tissue death during percutaneous thermal ablation with a chained neural cellular automata (NCA) architecture. The model does not output a heat map: it estimates cell death directly, which is what the planner needs. It trains down to 12,210 parameters and runs on basic 3D convolutions, so it works on a standard desktop computer. It computes 25 minutes of treatment at up to 476 fps, fast enough for interactive simulation and optimization loops.

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

{{< figure src="prediction_pipeline.png" title="Model Architecture" >}}
{{< figure src="TargetOutput.png" title="Target Output Pairs" >}}

{{< figure src="miccai2025-logo.png" width=50% alt="MICCAI 2025 Logo" >}}
{{< figure src="Planchette Logos.png" width=100% alt="Logos of collaborating institutions" >}}
