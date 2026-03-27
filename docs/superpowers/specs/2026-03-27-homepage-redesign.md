# Homepage Redesign — Design Spec

**Date:** 2026-03-27
**Status:** Approved

## Goal

Redesign the Axiom marketing homepage (`homepage/index.html` + `homepage/style.css`) to convert two audiences: DevOps/SRE engineers evaluating the tool, and managers/buyers who need to justify the purchase. The page follows a Problem → Solution narrative arc with a dashboard mockup to prove the product is real.

## Audiences & Conversion Paths

| Audience | Pain | CTA |
|---|---|---|
| DevOps / SRE | SSH sprawl, no audit trail, unsigned scripts | `docker compose up` — self-host in 30 min |
| Manager / Buyer | Risk, compliance, no control | Google Form — register Enterprise interest |

## Page Structure

### 1. Nav
- Logo (`⬡ Axiom`) left
- Right: `Docs` · `GitHub` · `Enterprise` button (primary colour, links to Google Form placeholder)
- Sticky or static — static is fine for v1

### 2. Hero
- **Eyebrow:** "Open-source orchestration"
- **Headline (problem-first):** "You have scripts running on dozens of servers. Are they safe?"
- **Subtext:** One sentence explaining the pull model + mTLS + Ed25519 signing
- **CTAs (side by side):**
  - Primary: `Self-host in 30 min →` → `./docs/getting-started/install/`
  - Secondary (outlined): `Talk to us about Enterprise` → Google Form placeholder

### 3. Dashboard Mockup
- Static HTML replica of the Nodes view
- Shows 2–3 nodes: online (green dot), offline (red dot), CPU percentage, capability tags (`python · bash`)
- Caption: "Real dashboard — no mock data in prod"
- Centred, max-width ~720px, styled to match the actual dashboard (dark surface, border, monospace tags)

### 4. Pain Points (3-column grid)
Three cards, each with an emoji icon, bold title, and 1–2 sentence description:

| Icon | Title | Body |
|---|---|---|
| 🔑 | SSH key sprawl | Keys on every server, revocation is manual, and you can't prove who ran what. |
| 📋 | No audit trail | Scripts ran. You think. Cron has no log of who triggered what or whether it succeeded. |
| ⚠️ | Unsigned execution | Any script that lands on a node runs. There's no verification it hasn't been tampered with. |

### 5. CE vs EE
**CE card** — unchanged from current page.

**EE card** — Option A treatment:
- `Coming soon` badge (crimson, top-left of card header)
- Feature list shown but text colour dimmed to `--axiom-text-faint`
- Bottom of card: `Interested in Enterprise? Get in touch →` — links to Google Form placeholder (`ENTERPRISE_FORM_URL`)
- Card border remains crimson (`--axiom-primary`) to keep visual weight

### 6. Dual CTA Section
Two side-by-side blocks, separated by a vertical rule on desktop, stacked on mobile:

**Left — DevOps:**
- Heading: "Cold-start in under 30 minutes"
- Subtext: "Full stack, no cloud account required."
- `docker compose -f compose.cold-start.yaml up -d` code block
- `Read the install guide →` text link

**Right — Buyers:**
- Heading: "Interested in Enterprise?"
- Subtext: "Tell us what you need. We'll be in touch."
- `Register your interest →` button → Google Form placeholder

### 7. Footer
- `© 2026 Axiom Laboratories. Apache 2.0 for Community Edition.`
- Links: GitHub · Docs

## Content Removals
- **Security prose section** (two long paragraphs on mTLS and Ed25519) — removed. The pain-points grid and hero subtext cover this more concisely.

## Design Tokens (unchanged)
All existing CSS custom properties (`--axiom-primary`, `--axiom-bg`, etc.) and fonts (Fira Sans / Fira Code) are preserved. No new dependencies.

## Google Form Placeholder
Use the constant `ENTERPRISE_FORM_URL` as an HTML comment at the top of `index.html` and in `href` attributes. Value: `#enterprise-interest` until the real form URL is known.

## Files Changed
- `homepage/index.html` — full rewrite
- `homepage/style.css` — additions: `.nav`, `.pain-grid`, `.dual-cta`, `.badge-coming-soon`, `.feature-list--dimmed`; existing rules retained

## Out of Scope
- Google Form creation (separate task, to follow)
- Animations or scroll effects
- Analytics/tracking scripts
- Light mode
