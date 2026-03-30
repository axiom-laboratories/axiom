# Design System Reference — Operator Guide

Extends the `codebase-to-course` design system with operator-guide-specific components. Include the full base token block, then add the operator tokens below.

---

## Base Tokens (same as codebase-to-course)

```css
:root {
  /* --- BACKGROUNDS --- */
  --color-bg:             #FAF7F2;
  --color-bg-warm:        #F5F0E8;
  --color-bg-code:        #1E1E2E;
  --color-text:           #2C2A28;
  --color-text-secondary: #6B6560;
  --color-text-muted:     #9E9790;
  --color-border:         #E5DFD6;
  --color-border-light:   #EEEBE5;
  --color-surface:        #FFFFFF;
  --color-surface-warm:   #FDF9F3;

  /* --- ACCENT --- adapt per product personality ---
     Operator guides benefit from slightly more conservative accents:
     teal (#2A7B9B), forest (#2D8B55), slate-blue (#3B5998).
     Avoid vermillion for operator guides — it reads as "danger". */
  --color-accent:         #2A7B9B;
  --color-accent-hover:   #1F6A87;
  --color-accent-light:   #E4F2F7;
  --color-accent-muted:   #5B9DB5;

  /* --- SEMANTIC --- */
  --color-success:        #2D8B55;
  --color-success-light:  #E8F5EE;
  --color-warning:        #B8860B;
  --color-warning-light:  #FFF8E1;
  --color-error:          #C93B3B;
  --color-error-light:    #FDE8E8;
  --color-info:           #2A7B9B;
  --color-info-light:     #E4F2F7;

  /* --- FONTS --- */
  --font-display: 'Bricolage Grotesque', Georgia, serif;
  --font-body:    'DM Sans', -apple-system, sans-serif;
  --font-mono:    'JetBrains Mono', 'Fira Code', monospace;

  /* --- TYPE SCALE --- */
  --text-xs:   0.75rem;
  --text-sm:   0.875rem;
  --text-base: 1rem;
  --text-lg:   1.125rem;
  --text-xl:   1.25rem;
  --text-2xl:  1.5rem;
  --text-3xl:  1.875rem;
  --text-4xl:  2.25rem;
  --text-5xl:  3rem;
  --text-6xl:  3.75rem;

  /* --- LINE HEIGHTS --- */
  --leading-tight:  1.15;
  --leading-snug:   1.3;
  --leading-normal: 1.6;

  /* --- SPACING --- */
  --space-1:  0.25rem;
  --space-2:  0.5rem;
  --space-3:  0.75rem;
  --space-4:  1rem;
  --space-5:  1.25rem;
  --space-6:  1.5rem;
  --space-8:  2rem;
  --space-10: 2.5rem;
  --space-12: 3rem;
  --space-16: 4rem;
  --space-20: 5rem;

  /* --- LAYOUT --- */
  --content-width:      800px;
  --content-width-wide: 1000px;
  --nav-height:         50px;
  --radius-sm:  8px;
  --radius-md:  12px;
  --radius-lg:  16px;
  --radius-full: 9999px;

  /* --- SHADOWS --- */
  --shadow-sm: 0 1px 2px rgba(44,42,40,0.05);
  --shadow-md: 0 4px 12px rgba(44,42,40,0.08);
  --shadow-lg: 0 8px 24px rgba(44,42,40,0.1);

  /* --- ANIMATION --- */
  --ease-out:    cubic-bezier(0.16,1,0.3,1);
  --ease-in-out: cubic-bezier(0.65,0,0.35,1);
  --duration-fast:   150ms;
  --duration-normal: 300ms;
  --duration-slow:   500ms;
  --stagger-delay:   120ms;
}
```

---

## Operator-Specific Additions

### Screenshot Frame

A polished placeholder that looks intentional — not broken. Used when real screenshots aren't embedded yet.

```css
.screenshot-frame {
  position: relative;
  background: #F0F4F8;
  border: 2px dashed #BCC8D4;
  border-radius: var(--radius-md);
  overflow: hidden;
  margin: var(--space-6) 0;
  box-shadow: var(--shadow-md);

  /* Default height — override per frame with style="--sh: Npx" */
  min-height: var(--sh, 280px);

  display: flex;
  align-items: center;
  justify-content: center;
}

/* Render actual image if src is provided */
.screenshot-frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* Placeholder content (shown when no img child) */
.screenshot-frame .sf-placeholder {
  text-align: center;
  padding: var(--space-8);
  color: #6B8099;
}
.sf-placeholder .sf-icon { font-size: 2rem; margin-bottom: var(--space-3); }
.sf-placeholder .sf-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--text-base);
  color: #3B5068;
  margin-bottom: var(--space-2);
}
.sf-placeholder .sf-desc {
  font-size: var(--text-sm);
  color: #6B8099;
  max-width: 320px;
  margin: 0 auto;
}

/* Top chrome bar (simulates browser/app chrome) */
.screenshot-frame .sf-chrome {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 32px;
  background: #E2E8EF;
  border-bottom: 1px solid #BCC8D4;
  display: flex;
  align-items: center;
  padding: 0 var(--space-3);
  gap: var(--space-2);
}
.sf-chrome-dot {
  width: 10px; height: 10px; border-radius: 50%;
}
.sf-chrome-dot:nth-child(1) { background: #FF5F57; }
.sf-chrome-dot:nth-child(2) { background: #FFBD2E; }
.sf-chrome-dot:nth-child(3) { background: #28C840; }

/* When chrome is present, push content below it */
.screenshot-frame.has-chrome .sf-placeholder {
  padding-top: calc(32px + var(--space-6));
}
```

**Usage — placeholder:**
```html
<!-- Add style="--sh: 350px" to set height -->
<div class="screenshot-frame has-chrome" style="--sh: 350px">
  <div class="sf-chrome">
    <div class="sf-chrome-dot"></div>
    <div class="sf-chrome-dot"></div>
    <div class="sf-chrome-dot"></div>
  </div>
  <div class="sf-placeholder">
    <div class="sf-icon">📸</div>
    <div class="sf-title">Screenshot: Jobs List View</div>
    <div class="sf-desc">Shows the Jobs page with a PENDING job highlighted in the queue, status badge visible</div>
  </div>
</div>
<!-- 🎥 RECORD THIS: Navigate to /jobs, dispatch a test job, capture the list view with PENDING status visible -->
```

**Usage — real image (base64 or path):**
```html
<div class="screenshot-frame has-chrome" style="--sh: 350px">
  <div class="sf-chrome">
    <div class="sf-chrome-dot"></div>
    <div class="sf-chrome-dot"></div>
    <div class="sf-chrome-dot"></div>
  </div>
  <img src="data:image/png;base64,iVBOR..." alt="Jobs list showing PENDING job">
</div>
```

---

### Annotation Overlays

Numbered callouts that point to specific areas of a screenshot. Works with both placeholder frames and real images.

```css
.screenshot-annotated {
  position: relative;
  display: inline-block;
  width: 100%;
}

.annotation {
  position: absolute;
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--color-error);   /* high-visibility red */
  color: white;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-sm);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 8px rgba(201,59,59,0.4);
  cursor: default;
  z-index: 10;
  /* Position via style="top: 30%; left: 65%" */
}

.annotation-legend {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-4);
}
.annotation-legend-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}
.annotation-legend-num {
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--color-error);
  color: white;
  font-weight: 700;
  font-family: var(--font-display);
  font-size: var(--text-xs);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
```

**Usage:**
```html
<div class="screenshot-annotated">
  <div class="screenshot-frame has-chrome" style="--sh: 300px">
    <!-- placeholder or img here -->
    <div class="annotation" style="top: 15%; left: 82%">1</div>
    <div class="annotation" style="top: 45%; left: 12%">2</div>
    <div class="annotation" style="top: 72%; left: 48%">3</div>
    <div class="sf-placeholder">
      <div class="sf-icon">📸</div>
      <div class="sf-title">Screenshot: Dispatch Form</div>
      <div class="sf-desc">The new job dispatch modal with form fields visible</div>
    </div>
  </div>
  <div class="annotation-legend">
    <div class="annotation-legend-item">
      <div class="annotation-legend-num">1</div>
      <span><strong>Dispatch button</strong> — top-right of the Jobs page header</span>
    </div>
    <div class="annotation-legend-item">
      <div class="annotation-legend-num">2</div>
      <span><strong>Capability requirements</strong> — filter which nodes can run this job</span>
    </div>
    <div class="annotation-legend-item">
      <div class="annotation-legend-num">3</div>
      <span><strong>Sign & Submit</strong> — only active after a signing key is selected</span>
    </div>
  </div>
</div>
```

---

### GIF Player Frame

A styled container for animated demonstrations. Supports embedded base64 GIFs or external URLs. Shows a polished placeholder when no GIF is provided yet.

```css
.gif-player {
  position: relative;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #1A1A2E;
  margin: var(--space-6) 0;
  box-shadow: var(--shadow-lg);
  min-height: var(--gh, 240px);
  cursor: pointer;
}

.gif-player img {
  width: 100%;
  display: block;
}

/* Play overlay (shown before first click) */
.gif-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(26,26,46,0.85);
  color: white;
  gap: var(--space-4);
  transition: opacity var(--duration-normal);
}
.gif-overlay.hidden { opacity: 0; pointer-events: none; }

.gif-play-btn {
  width: 64px; height: 64px;
  border-radius: 50%;
  border: 3px solid white;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem;
  transition: transform var(--duration-fast), background var(--duration-fast);
}
.gif-player:hover .gif-play-btn {
  background: rgba(255,255,255,0.15);
  transform: scale(1.1);
}

.gif-label {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--text-base);
  text-align: center;
  padding: 0 var(--space-6);
}

.gif-sublabel {
  font-size: var(--text-sm);
  opacity: 0.7;
  text-align: center;
  padding: 0 var(--space-8);
}

/* Placeholder state (no GIF provided) */
.gif-player.placeholder {
  cursor: default;
  background: #1E2A3A;
}
.gif-player.placeholder .gif-play-btn {
  border-color: rgba(255,255,255,0.3);
  color: rgba(255,255,255,0.3);
}
.gif-record-note {
  font-size: var(--text-xs);
  color: rgba(255,255,255,0.4);
  font-family: var(--font-mono);
  text-align: center;
  padding: 0 var(--space-6);
}
```

**Usage — placeholder:**
```html
<div class="gif-player placeholder" style="--gh: 280px">
  <div class="gif-overlay">
    <div class="gif-play-btn">▶</div>
    <div class="gif-label">Walkthrough: Dispatching Your First Job</div>
    <div class="gif-sublabel">Shows the full flow from opening the dispatch form to seeing the job appear in the queue</div>
    <div class="gif-record-note">🎥 Record: Open /jobs → click Dispatch → fill form → submit → capture until status shows PENDING</div>
  </div>
</div>
```

**Usage — with real GIF (click to play):**
```html
<div class="gif-player" style="--gh: 280px" onclick="playGif(this)">
  <img src="data:image/gif;base64,R0lGOD..." alt="Dispatching a job" style="display:none">
  <div class="gif-overlay">
    <div class="gif-play-btn">▶</div>
    <div class="gif-label">Walkthrough: Dispatching Your First Job</div>
    <div class="gif-sublabel">Click to play (20 seconds)</div>
  </div>
</div>
```

**JS for gif play:**
```javascript
window.playGif = function(player) {
  const img = player.querySelector('img');
  const overlay = player.querySelector('.gif-overlay');
  if (!img) return;
  img.style.display = 'block';
  overlay.classList.add('hidden');
};
```

---

### Keyboard Shortcut Badge

```css
.kbd {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.key {
  display: inline-block;
  padding: 2px 7px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-bottom: 2px solid var(--color-border);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text);
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
```

**Usage:** `<span class="kbd"><span class="key">Ctrl</span><span class="key">Shift</span><span class="key">D</span></span>`

---

### Status Badges

For showing job statuses, node states etc. inline in guide text:

```css
.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.status-pending  { background: #FFF8E1; color: #B8860B; border: 1px solid #F0D060; }
.status-running  { background: #E4F2F7; color: #1F6A87; border: 1px solid #9DC8DC; }
.status-complete { background: var(--color-success-light); color: var(--color-success); border: 1px solid #A8D8B8; }
.status-failed   { background: var(--color-error-light); color: var(--color-error); border: 1px solid #E8A8A8; }
.status-revoked  { background: #F5F0E8; color: #7B6B5A; border: 1px solid #C8B898; }
```

**Usage:** `<span class="status-badge status-pending">PENDING</span>`

---

## Callout Variants (Operator-Specific)

```css
/* Tip — green left border, used for faster paths / power-user tricks */
.callout-tip    { background: var(--color-success-light); border-left: 4px solid var(--color-success); }

/* Warning — amber left border, used for caution-worthy actions */
.callout-warning { background: var(--color-warning-light); border-left: 4px solid var(--color-warning); }

/* Danger — red left border, used for irreversible actions */
.callout-danger  { background: var(--color-error-light); border-left: 4px solid var(--color-error); }

/* Info — accent colour, used for "good to know" context */
.callout-info   { background: var(--color-accent-light); border-left: 4px solid var(--color-accent); }
```

---

## Responsive Rules

```css
/* Tablet */
@media (max-width: 768px) {
  :root { --text-4xl: 1.875rem; --text-5xl: 2.25rem; --text-6xl: 3rem; }
  .annotation-legend { margin-top: var(--space-3); }
  .before-after { grid-template-columns: 1fr; }
}

/* Mobile */
@media (max-width: 480px) {
  :root { --text-4xl: 1.5rem; --text-5xl: 1.875rem; --text-6xl: 2.25rem; }
  .module { padding: var(--space-8) var(--space-4); }
  .step-cards { gap: var(--space-2); }
}
```
