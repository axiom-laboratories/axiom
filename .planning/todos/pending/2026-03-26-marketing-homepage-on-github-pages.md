---
created: 2026-03-26T21:32:05.519Z
title: Marketing homepage on GitHub Pages
area: docs
files: []
---

## Problem

Axiom has no public-facing marketing page. Potential users/evaluators land on the GitHub repo with no polished first impression. Need a lightweight homepage to communicate what Axiom is, why it exists, and how to get started — without requiring any hosting infrastructure.

## Solution

Use GitHub Pages for the initial marketing site (zero ops cost, ships with the repo):

- Create a `gh-pages` branch or a `docs/` subdirectory on a separate repo (e.g. `axiom-laboratories/axiom-labs.github.io` or a dedicated `axiom-laboratories/axiom-homepage` repo)
- Static HTML/CSS — no framework required for v1, or use a lightweight generator (Astro, Hugo, 11ty)
- Key sections: hero (what it is), features (node fleet, job dispatch, Foundry, RBAC, audit log), quick-start CTA (link to docs), CE vs EE comparison table
- Link from the main repo README and the MkDocs docs site
- Can be replaced with a proper domain + hosting later without any code changes — GitHub Pages supports custom domains
