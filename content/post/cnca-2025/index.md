---
title: "C-NCA : Chained Neural Cellular Automata"
description: "Method for fast and accurate thermal ablation estimation using C-NCA."
slug: cnca-2025
date: 2025-09-22 00:00:00+0000
image: TargetOutput.png
categories:
    - Research

links:
- title: "E-Poster"
  description: "E-Poster presented at MICCAI 2025"
  website: cnca-e-poster.pdf

---

## Description
We introduced an approach to estimate the heat induced tissue death in percutaneous thermal ablation based on a chained NCA architecture. While not directly producing a heat map, it accurately estimates cell death induced by thermal damage by implicitly modeling temperature field effects and evolution, going beyond heat distribution, with <b>low root mean square error and high speed</b>. The model is <b>computationally efficient</b>, characterized by a mere <b>12,210 learned parameters</b>, and is capable of operating on a standard desktop computer due to its implementation through basic 3D convolutions. It can compute 25 minutes of treatment at a frequency up to <b>476 fps</b>, making it suitable for interactive simulations and optimization loops.

{{< figure src="prediction_pipeline.png" title="Model Architecture" >}}
{{< figure src="TargetOutput.png" title="Target Output Pairs" >}}

<!--Add all the logos side by side-->
{{< figure src="Planchette Logos.png" width=100% alt="Logos of collaborating institutions" >}}
