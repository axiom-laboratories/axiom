---
created: 2026-03-28T17:26:51.990Z
title: Add screenshots and marketing images to standalone marketing page
area: docs
files:
  - homepage/index.html
  - homepage/style.css
---

## Problem

The marketing homepage (`homepage/index.html`) deployed to GitHub Pages is currently text-only. Evaluators and potential users have no visual impression of the product before installing — no dashboard screenshots, no job dispatch UI, no node monitoring view.

## Solution

- Capture screenshots of key UI views from a running stack: Dashboard overview, Nodes (sparkline charts), Jobs queue, Foundry wizard, and Job Definitions
- Add a product screenshot section to `homepage/index.html` — either a carousel/lightbox or a static grid of annotated images
- Consider a hero image or animated GIF showing the node fleet + job dispatch flow
- Store images under `homepage/assets/` and reference them locally (not CDN) so they deploy cleanly via `homepage-deploy.yml`
- Optionally: a short screen recording (converted to GIF/WebM) of the hello-world flow end-to-end for the USP section
