# Homepage Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the Axiom marketing homepage to follow a Problem → Solution narrative arc with a dashboard mockup, two audience-specific CTAs, and an Enterprise Edition "Coming soon" treatment.

**Architecture:** Two static files — `homepage/index.html` (full rewrite) and `homepage/style.css` (additions to existing rules). No JavaScript, no build step. Deployed via `gh-pages-deploy.yml` which is already wired up.

**Tech Stack:** Plain HTML5, CSS custom properties, Google Fonts (Fira Sans / Fira Code — already loaded)

---

## File Map

| Action | File | What changes |
|--------|------|-------------|
| Rewrite | `homepage/index.html` | New structure: nav → hero → mockup → pain points → CE/EE → dual CTA → footer |
| Modify | `homepage/style.css` | Add: `.site-nav`, `.pain-grid`, `.pain-card`, `.dual-cta`, `.badge-coming-soon`, `.feature-list--dimmed`, `.mockup-panel`; existing rules kept |

---

### Task 1: Add nav bar styles + HTML

The current page has no `<nav>`. Add a sticky-top nav with logo, Docs, GitHub, and an Enterprise button.

**Files:**
- Modify: `homepage/style.css`
- Modify: `homepage/index.html`

- [ ] **Step 1: Add nav CSS to `style.css`**

Append to the end of `homepage/style.css`:

```css
/* ----- Site nav ----- */
.site-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background-color: rgba(13, 17, 23, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--axiom-border);
}

.site-nav .container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-block: 0.875rem;
}

.nav-logo {
  font-size: 1rem;
  font-weight: 700;
  color: var(--axiom-text);
  text-decoration: none;
  letter-spacing: -0.01em;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.nav-links a {
  color: var(--axiom-text-muted);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: color 0.15s ease;
}

.nav-links a:hover {
  color: var(--axiom-text);
}

.nav-links .btn-nav-enterprise {
  color: #fff;
  background-color: var(--axiom-primary);
  border-radius: var(--radius);
  padding: 0.4rem 1rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.nav-links .btn-nav-enterprise:hover {
  background-color: var(--axiom-primary-hover);
  color: #fff;
}
```

- [ ] **Step 2: Add nav HTML to `index.html`**

Replace the opening `<body>` tag with:

```html
<body>

  <!-- Nav -->
  <nav class="site-nav">
    <div class="container">
      <a href="/" class="nav-logo">⬡ Axiom</a>
      <div class="nav-links">
        <a href="./docs/">Docs</a>
        <a href="https://github.com/axiom-laboratories/axiom">GitHub</a>
        <a href="#enterprise-interest" class="btn-nav-enterprise">Enterprise</a>
      </div>
    </div>
  </nav>
```

- [ ] **Step 3: Visual check**

Open `homepage/index.html` in a browser (file://). Verify:
- Nav bar appears at top with logo left, links right
- Enterprise button is crimson
- Page scrolls and nav stays fixed

- [ ] **Step 4: Commit**

```bash
git add homepage/index.html homepage/style.css
git commit -m "feat(homepage): add sticky nav bar"
```

---

### Task 2: Rewrite the hero section (problem-first)

Replace the current centred headline with a problem-first hook.

**Files:**
- Modify: `homepage/index.html`
- Modify: `homepage/style.css`

- [ ] **Step 1: Replace the hero HTML**

Find the `<!-- Hero -->` section in `index.html` and replace it entirely:

```html
  <!-- Hero -->
  <section class="hero">
    <div class="container">
      <p class="section-label">Open-source orchestration</p>
      <h1>You have scripts running on<br>dozens of servers. Are they safe?</h1>
      <p class="hero-sub">
        Axiom replaces SSH&nbsp;+&nbsp;crontab sprawl with a pull-model orchestrator —
        every node mTLS-verified, every script Ed25519-signed before it runs.
      </p>
      <div class="cta-group">
        <a href="./docs/getting-started/install/" class="btn btn-primary">Self-host in 30 min &rarr;</a>
        <a href="#enterprise-interest" class="btn btn-secondary">Talk to us about Enterprise</a>
      </div>
    </div>
  </section>
```

- [ ] **Step 2: Visual check**

Open in browser. Verify headline reads "You have scripts running on dozens of servers. Are they safe?" and both CTA buttons are present.

- [ ] **Step 3: Commit**

```bash
git add homepage/index.html
git commit -m "feat(homepage): problem-first hero headline"
```

---

### Task 3: Add dashboard mockup section

New section between the hero and the current security section. Shows a static replica of the Nodes view.

**Files:**
- Modify: `homepage/index.html`
- Modify: `homepage/style.css`

- [ ] **Step 1: Add mockup CSS**

Append to `homepage/style.css`:

```css
/* ----- Dashboard mockup ----- */
.mockup-section {
  padding-block: 3rem;
  border-bottom: 1px solid var(--axiom-border);
  text-align: center;
}

.mockup-panel {
  display: inline-block;
  text-align: left;
  background-color: var(--axiom-surface);
  border: 1px solid var(--axiom-border);
  border-radius: var(--radius);
  padding: 1.25rem;
  max-width: 680px;
  width: 100%;
}

.mockup-panel-tabs {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--axiom-border);
  padding-bottom: 0.75rem;
}

.mockup-tab {
  font-size: 0.875rem;
  color: var(--axiom-text-muted);
  font-weight: 500;
}

.mockup-tab--active {
  color: var(--axiom-text);
  font-weight: 600;
  border-bottom: 2px solid var(--axiom-primary);
  padding-bottom: 0.1rem;
  margin-bottom: -0.85rem;
}

.mockup-node-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--axiom-border);
  font-size: 0.875rem;
}

.mockup-node-row:last-child {
  border-bottom: none;
}

.node-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.node-status--online  { background-color: #3fb950; }
.node-status--offline { background-color: var(--axiom-primary); }

.node-name {
  color: var(--axiom-text);
  font-weight: 500;
  flex: 1;
  min-width: 0;
}

.node-name--offline {
  color: var(--axiom-text-muted);
}

.node-caps {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.node-cap-tag {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  background-color: var(--axiom-bg);
  border: 1px solid var(--axiom-border);
  border-radius: 3px;
  padding: 0.1rem 0.4rem;
  color: var(--axiom-text-muted);
}

.node-cpu {
  font-size: 0.8rem;
  color: var(--axiom-text-muted);
  white-space: nowrap;
}

.node-cpu strong {
  color: var(--axiom-text);
}

.mockup-caption {
  font-size: 0.8rem;
  color: var(--axiom-text-faint);
  margin-top: 0.75rem;
}
```

- [ ] **Step 2: Add mockup HTML**

Insert this section immediately after the closing `</section>` of the hero, before the `<!-- Security -->` section:

```html
  <!-- Dashboard mockup -->
  <section class="mockup-section">
    <div class="container">
      <div class="mockup-panel">
        <div class="mockup-panel-tabs">
          <span class="mockup-tab mockup-tab--active">Nodes</span>
          <span class="mockup-tab">Jobs</span>
          <span class="mockup-tab">Audit log</span>
        </div>
        <div class="mockup-node-row">
          <span class="node-status node-status--online"></span>
          <span class="node-name">node-alpha</span>
          <div class="node-caps">
            <span class="node-cap-tag">python</span>
            <span class="node-cap-tag">bash</span>
          </div>
          <span class="node-cpu">CPU <strong>23%</strong></span>
        </div>
        <div class="mockup-node-row">
          <span class="node-status node-status--online"></span>
          <span class="node-name">node-beta</span>
          <div class="node-caps">
            <span class="node-cap-tag">python</span>
            <span class="node-cap-tag">powershell</span>
          </div>
          <span class="node-cpu">CPU <strong>61%</strong></span>
        </div>
        <div class="mockup-node-row">
          <span class="node-status node-status--offline"></span>
          <span class="node-name node-name--offline">node-gamma</span>
          <div class="node-caps"></div>
          <span class="node-cpu" style="color:var(--axiom-text-faint)">offline · 4h ago</span>
        </div>
      </div>
      <p class="mockup-caption">Real dashboard — no mock data in prod</p>
    </div>
  </section>
```

- [ ] **Step 3: Visual check**

Open in browser. Verify the mockup panel appears below the hero, tabs are visible, node rows show status dots, capability tags, and CPU.

- [ ] **Step 4: Commit**

```bash
git add homepage/index.html homepage/style.css
git commit -m "feat(homepage): add dashboard mockup section"
```

---

### Task 4: Replace security prose with 3-column pain points

Remove the two-paragraph "Security without compromise" section. Replace with a 3-column pain points grid.

**Files:**
- Modify: `homepage/index.html`
- Modify: `homepage/style.css`

- [ ] **Step 1: Add pain grid CSS**

Append to `homepage/style.css`:

```css
/* ----- Pain points grid ----- */
.pain-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  margin-top: 2rem;
}

.pain-card {
  background-color: var(--axiom-surface);
  border: 1px solid var(--axiom-border);
  border-radius: var(--radius);
  padding: 1.25rem;
}

.pain-icon {
  font-size: 1.5rem;
  margin-bottom: 0.6rem;
  display: block;
}

.pain-card h3 {
  font-size: 1rem;
  margin-bottom: 0.4rem;
}

.pain-card p {
  font-size: 0.875rem;
  color: var(--axiom-text-muted);
  line-height: 1.55;
}

@media (max-width: 640px) {
  .pain-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 2: Replace the security section HTML**

Find the `<!-- Security -->` comment and replace the entire section with:

```html
  <!-- Pain points -->
  <section class="section">
    <div class="container">
      <p class="section-label">The problem</p>
      <h2>SSH&nbsp;+&nbsp;crontab doesn't scale</h2>
      <div class="pain-grid">
        <div class="pain-card">
          <span class="pain-icon">🔑</span>
          <h3>SSH key sprawl</h3>
          <p>Keys on every server, revocation is manual, and you can't prove who ran what.</p>
        </div>
        <div class="pain-card">
          <span class="pain-icon">📋</span>
          <h3>No audit trail</h3>
          <p>Scripts ran. You think. Cron has no log of who triggered what or whether it succeeded.</p>
        </div>
        <div class="pain-card">
          <span class="pain-icon">⚠️</span>
          <h3>Unsigned execution</h3>
          <p>Any script that lands on a node runs. There's no verification it hasn't been tampered with.</p>
        </div>
      </div>
    </div>
  </section>
```

- [ ] **Step 3: Visual check**

Confirm the long security prose is gone and 3 cards appear in a grid.

- [ ] **Step 4: Commit**

```bash
git add homepage/index.html homepage/style.css
git commit -m "feat(homepage): replace security prose with pain points grid"
```

---

### Task 5: Apply "Coming soon" treatment to the EE card

Add a badge, dim the feature list, and add the "Get in touch" link. Keep CE card unchanged.

**Files:**
- Modify: `homepage/index.html`
- Modify: `homepage/style.css`

- [ ] **Step 1: Add coming-soon CSS**

Append to `homepage/style.css`:

```css
/* ----- Coming soon badge ----- */
.badge-coming-soon {
  background-color: rgba(210, 53, 86, 0.12);
  color: var(--axiom-primary);
  border: 1px solid rgba(210, 53, 86, 0.35);
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.2em 0.55em;
  border-radius: 4px;
}

/* ----- Dimmed feature list (EE coming soon) ----- */
.feature-list--dimmed li {
  color: var(--axiom-text-faint);
}

.feature-list--dimmed li::before {
  color: var(--axiom-text-faint);
}

/* ----- EE interest link ----- */
.ee-interest {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--axiom-border);
  font-size: 0.875rem;
  color: var(--axiom-text-muted);
}

.ee-interest a {
  color: var(--axiom-primary);
  text-decoration: none;
  font-weight: 600;
}

.ee-interest a:hover {
  text-decoration: underline;
}
```

- [ ] **Step 2: Update EE card HTML**

Find the `<div class="card card-ee">` block in `index.html`. Make these three changes:

1. In the `card-header` div, add the badge after the `<h3>`:
```html
<span class="badge badge-coming-soon">Coming soon</span>
```
Replace the existing `<span class="badge badge-ee">Commercial licence</span>` with the above.

2. Add `feature-list--dimmed` class to the EE `<ul>`:
```html
<ul class="feature-list feature-list--dimmed">
```

3. After the closing `</ul>`, add the interest link (before `</div>` closing the card):
```html
        <div class="ee-interest">
          Interested in Enterprise? <a href="#enterprise-interest">Get in touch &rarr;</a>
        </div>
```

- [ ] **Step 3: Visual check**

Confirm EE card shows "Coming soon" badge (crimson), feature list is visibly dimmer than CE list, and "Get in touch" link appears at the bottom.

- [ ] **Step 4: Commit**

```bash
git add homepage/index.html homepage/style.css
git commit -m "feat(homepage): EE coming-soon badge and dimmed feature list"
```

---

### Task 6: Add dual CTA section and remove old install section

Replace the existing "Quick Install" section with a two-column dual CTA block — DevOps on the left, Enterprise interest form on the right.

**Files:**
- Modify: `homepage/index.html`
- Modify: `homepage/style.css`

- [ ] **Step 1: Add dual CTA CSS**

Append to `homepage/style.css`:

```css
/* ----- Dual CTA section ----- */
.dual-cta {
  display: grid;
  grid-template-columns: 1fr 1px 1fr;
  gap: 0;
  align-items: start;
}

.dual-cta-divider {
  background-color: var(--axiom-border);
  align-self: stretch;
  margin-inline: 2rem;
}

.dual-cta-block {
  padding: 0.5rem 0;
}

.dual-cta-block h3 {
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
}

.dual-cta-block .install-sub {
  margin-bottom: 1.25rem;
}

@media (max-width: 640px) {
  .dual-cta {
    grid-template-columns: 1fr;
  }

  .dual-cta-divider {
    height: 1px;
    margin: 2rem 0;
    background-color: var(--axiom-border);
  }
}
```

- [ ] **Step 2: Replace the Quick Install section HTML**

Find the `<!-- Quick Install -->` section and replace it entirely with:

```html
  <!-- Dual CTA -->
  <section class="section" id="enterprise-interest">
    <div class="container">
      <div class="dual-cta">

        <div class="dual-cta-block">
          <p class="section-label">Get started</p>
          <h3>Cold-start in under 30 minutes</h3>
          <p class="install-sub">Full stack, no cloud account required.</p>
          <pre><code>docker compose -f compose.cold-start.yaml up -d</code></pre>
          <a href="./docs/getting-started/install/" class="text-link">Read the install guide &rarr;</a>
        </div>

        <div class="dual-cta-divider" aria-hidden="true"></div>

        <div class="dual-cta-block">
          <p class="section-label">Enterprise edition</p>
          <h3>Interested in Enterprise?</h3>
          <p class="install-sub">Tell us what you need. We'll be in touch when Enterprise Edition launches.</p>
          <a href="#enterprise-interest" class="btn btn-primary">Register your interest &rarr;</a>
        </div>

      </div>
    </div>
  </section>
```

**Note:** `ENTERPRISE_FORM_URL` is a placeholder. Replace with the real Google Form URL once created.

- [ ] **Step 3: Visual check**

Two columns side by side on desktop. Left shows `docker compose` snippet, right shows "Register your interest" button. On mobile (resize to <640px) they stack.

- [ ] **Step 4: Commit**

```bash
git add homepage/index.html homepage/style.css
git commit -m "feat(homepage): dual CTA section — self-host and enterprise interest"
```

---

### Task 7: Update footer year and push to verify deployment

Minor: update copyright year from 2025 → 2026, then push to trigger `gh-pages-deploy.yml` and confirm both URLs serve correctly.

**Files:**
- Modify: `homepage/index.html`

- [ ] **Step 1: Update footer year**

Find in `index.html`:
```html
<p>&copy; 2025 Axiom Laboratories.
```
Change to:
```html
<p>&copy; 2026 Axiom Laboratories.
```

- [ ] **Step 2: Final local check**

Open `homepage/index.html` in browser. Walk through the full page top to bottom:
- [ ] Nav: logo, Docs, GitHub, Enterprise button
- [ ] Hero: problem-first headline, two CTAs
- [ ] Dashboard mockup: 3 nodes with status, caps, CPU
- [ ] Pain points: 3 cards in a grid
- [ ] CE card: unchanged
- [ ] EE card: "Coming soon" badge, dimmed list, "Get in touch" link
- [ ] Dual CTA: `docker compose` snippet left, Enterprise interest right
- [ ] Footer: 2026

- [ ] **Step 3: Commit and push**

```bash
git add homepage/index.html
git commit -m "feat(homepage): update footer year, complete redesign"
git push origin main
```

- [ ] **Step 4: Verify deployment**

Wait ~60s for `gh-pages-deploy.yml` to complete, then check:
- `https://axiom-laboratories.github.io/axiom/` — marketing homepage (not MkDocs)
- `https://axiom-laboratories.github.io/axiom/docs/` — MkDocs docs

---

## Swapping in the real Google Form URL

The Enterprise CTA button currently uses `href="#enterprise-interest"` (smooth-scrolls to the dual CTA section — functional in the meantime). Once the Google Form is ready, update the two `href` values in `index.html`:

1. Nav Enterprise button: `href="#enterprise-interest"` → Google Form URL
2. "Register your interest" button in the dual CTA block: same change

```bash
sed -i 's|href="#enterprise-interest"|href="https://forms.google.com/YOUR_FORM_ID"|g' homepage/index.html
```

Then commit and push to redeploy.
