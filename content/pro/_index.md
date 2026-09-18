---
title: "Professional"
description: "PhD student in computer-assisted interventions at ICube Laboratory, University of Strasbourg."
layout: "hub-pro"
eyebrow: "ICube Laboratory · University of Strasbourg"
headline: "Thermal ablation planning, |in real time|."
tagline: "Percutaneous thermal ablation treats liver tumors with needle-mounted heat. When one needle is not enough, clinicians must plan several overlapping ablations, and local recurrence reaches 10 to 39% within five years. My PhD builds the planning software that runs fast enough to use during the procedure."
now: "Building the multi-needle replanning loop on the C-NCA estimator"
cells:
  - k: "Publications"
    v: "3"
    sub: "MICCAI ×2 · IJCARS ×1"
    acc: true
  - k: "Station pulse"
    pulse: true
    sub: "visitors · 7 days"
  - k: "Research routes"
    v: "3"
    sub: "simulation → planning → translation"
  - k: "Funding"
    v: "ITI"
    sub: "HealthTech doctoral program"
routes:
  - no: "R1 · SIMULATION"
    status: "SHIPPED"
    st: "ship"
    title: "Make heat computable"
    metric: "2 papers · in the planning loop"
    desc: "C-NCA estimates tissue death fast enough to plan interactively; HEAT computes the ablation zone in under a second."
    url: "/pro/research/cnca-2025/"
  - no: "R2 · PLANNING"
    status: "IN PROGRESS"
    st: "wip"
    title: "Make plans real-time"
    metric: "multi-needle · replanning"
    desc: "Automatic multi-needle placement and adaptive replanning, built on the C-NCA estimator and the CryoTrack workflow."
    url: "/pro/research/2024-cryotrack-miccai/"
  - no: "R3 · CLINICAL"
    status: "EARLY"
    st: "early"
    title: "Make it clinical"
    metric: "ITI HealthTech"
    desc: "Planning interfaces designed and tested with clinicians at the IHU, inside the operating-room loop."
    url: "/pro/about/"
featuredPubs:
  - "/pro/research/cnca-2025"
  - "/pro/research/2025-heat-ijcars"
workbench:
  - group: "Core"
    items: ["Python", "C++"]
  - group: "Surgical platforms"
    items: ["3D Slicer", "OpenIGTLink"]
  - group: "Interactive & 3D"
    items: ["Unity", "Godot", "Blender"]
  - group: "This station"
    items: ["Hugo", "Caddy", "SQLite"]
timeline:
  - period: "2024 —"
    title: "PhD Student, Computer-Assisted Interventions"
    place: "ICube Laboratory · University of Strasbourg"
    desc: "Automatic multi-needle adaptive planning for percutaneous thermal ablation, funded by the ITI HealthTech doctoral program."
    out: "axis: multi-needle adaptive planning"
  - period: "2023 — 2024"
    title: "R&D Internships in Computer-Assisted Surgery"
    place: "TU Darmstadt · IHU Strasbourg · ICube"
    desc: "Took over and enhanced CryoTrack; GPU-accelerated thermal ablation simulation."
    out: "real-time MR planning · CryoTrack handover"
    url: "/pro/research/2024-assisted-surgery-internship/"
  - period: "2022"
    title: "Research Internship in Computer Science"
    place: "University of Oviedo, Spain"
    desc: "Full research project, published on PeerJ Computer Science."
    out: "complete pipeline → PeerJ paper"
    url: "/pro/research/2022-research-internship/"
  - period: "2020"
    title: "Research Internship — Landslide Monitoring"
    place: "EOST, Strasbourg"
    desc: "Python data-analysis tool for landslide surveillance."
    out: "GKA landslide analyzer, open source"
    url: "/pro/research/2020-landslide-monitoring/"
talks:
  - venue: "MICCAI 2024 · Marrakesh"
    what: "CryoTrack, presented during the conference"
    url: "/pro/research/2024-cryotrack-miccai/"
  - venue: "MICCAI 2025 · Seoul"
    what: "C-NCA, e-poster session"
    url: "/pro/research/cnca-2025/"
repos:
  - name: "UniNet"
    lang: "C++"
    desc: "Unified networking library for fast cross-platform data transfer."
    url: "https://github.com/JonasMht/UniNet"
  - name: "TER_CNN_Compression"
    lang: "Jupyter"
    desc: "Master's research project: CNN compression for medical imaging."
    url: "https://github.com/JonasMht/TER_CNN_Compression"
  - name: "GKA_file_manipulation_software"
    lang: "Python"
    desc: "EOST internship: landslide data analyzer (statistics and charts)."
    url: "https://github.com/JonasMht/GKA_file_manipulation_software"
  - name: "Sensha-Game-2019"
    lang: "Python"
    desc: "2D real-time strategy tank game built with PyGame — where the workshop started."
    url: "https://github.com/JonasMht/Sensha-Game-2019"
---

My research topic is **percutaneous thermal ablation**, a minimally invasive
treatment for small liver tumors. When a tumor exceeds what a single needle can
cover, clinicians must plan multiple overlapping ablations manually, and local
recurrence rates reach 10 to 39&nbsp;% within five years.

My PhD works on three parts of this problem: faster simulation, replanning
during the procedure, and the interfaces clinicians use to do both.
