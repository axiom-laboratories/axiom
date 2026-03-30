# Interactive Elements Reference — Operator Guide

Implementation patterns for every interactive element used in operator guides. The primary teaching tools here are **screenshots, GIFs, step-by-step click guides, and workflow quizzes** — not code blocks.

## Table of Contents
1. [Step-by-Step Click Guide](#step-by-step-click-guide)
2. [Annotated Screenshot Frame](#annotated-screenshot-frame)
3. [GIF Player](#gif-player)
4. [Before/After Screenshot Comparison](#beforeafter-screenshot-comparison)
5. [Workflow Scenario Quiz](#workflow-scenario-quiz)
6. [Callout Boxes (Tip / Warning / Danger)](#callout-boxes)
7. [Status Flow Diagram](#status-flow-diagram)
8. [Keyboard Shortcut Reference](#keyboard-shortcut-reference)
9. [Glossary Tooltips](#glossary-tooltips)
10. [Feature/Section Cards](#featuresection-cards)
11. [Tabbed Procedure Switcher](#tabbed-procedure-switcher)
12. [Progress Checklist](#progress-checklist)

---

## Step-by-Step Click Guide

The most important operator guide element. Shows a numbered sequence of UI actions with optional mini-screenshot per step.

**HTML:**
```html
<div class="click-guide">
  <div class="cg-step">
    <div class="cg-num">1</div>
    <div class="cg-body">
      <strong class="cg-action">Open the Jobs page</strong>
      <p class="cg-detail">Click <strong>Jobs</strong> in the left sidebar. The job queue loads showing all recent jobs.</p>
      <!-- Optional: small inline screenshot for this step -->
      <div class="screenshot-frame" style="--sh: 80px; margin: var(--space-3) 0;">
        <div class="sf-placeholder">
          <div class="sf-desc">Sidebar with Jobs highlighted</div>
        </div>
      </div>
    </div>
  </div>
  <div class="cg-step">
    <div class="cg-num">2</div>
    <div class="cg-body">
      <strong class="cg-action">Click the Dispatch button</strong>
      <p class="cg-detail">Top-right corner of the Jobs page. Opens the dispatch modal.</p>
    </div>
  </div>
  <div class="cg-step">
    <div class="cg-num">3</div>
    <div class="cg-body">
      <strong class="cg-action">Fill in the script and requirements</strong>
      <p class="cg-detail">Paste your Python script in the Script field. Set <strong>Runtime</strong> to Python. Add any <span class="term" data-definition="Capability requirements filter which nodes can run this job — e.g. requiring 'python:3.9' means only nodes that have Python 3.9+ installed will pick it up.">capability requirements</span> if needed.</p>
    </div>
  </div>
  <div class="cg-step cg-step--final">
    <div class="cg-num">✓</div>
    <div class="cg-body">
      <strong class="cg-action">Click Sign & Submit</strong>
      <p class="cg-detail">The job appears in the queue with status <span class="status-badge status-pending">PENDING</span>. A node will pick it up within seconds.</p>
    </div>
  </div>
</div>
```

**CSS:**
```css
.click-guide {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin: var(--space-6) 0;
  position: relative;
}

/* Vertical connecting line */
.click-guide::before {
  content: '';
  position: absolute;
  left: 19px;
  top: 28px;
  bottom: 28px;
  width: 2px;
  background: var(--color-border);
}

.cg-step {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
  margin-bottom: var(--space-2);
  position: relative;
  z-index: 1;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
}
.cg-step:hover { border-color: var(--color-accent-muted); box-shadow: var(--shadow-sm); }

.cg-num {
  width: 38px; height: 38px;
  border-radius: 50%;
  background: var(--color-accent);
  color: white;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-sm);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.cg-step--final .cg-num {
  background: var(--color-success);
}

.cg-action {
  display: block;
  font-size: var(--text-base);
  color: var(--color-text);
  margin-bottom: var(--space-1);
}

.cg-detail {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin: 0;
  line-height: var(--leading-normal);
}
```

---

## Annotated Screenshot Frame

See `design-system.md` for full CSS. Here's the complete HTML pattern with hover-highlight annotations:

**HTML with hover behaviour:**
```html
<div class="screenshot-annotated" style="margin: var(--space-6) 0">
  <div class="screenshot-frame has-chrome" style="--sh: 320px">
    <div class="sf-chrome">
      <div class="sf-chrome-dot"></div>
      <div class="sf-chrome-dot"></div>
      <div class="sf-chrome-dot"></div>
    </div>
    <!-- Annotations positioned over the screenshot area -->
    <!-- Coordinates are % from top-left of the frame -->
    <div class="annotation" style="top: 20%; left: 85%" data-ann="1">1</div>
    <div class="annotation" style="top: 50%; left: 18%" data-ann="2">2</div>
    <div class="annotation" style="top: 78%; left: 55%" data-ann="3">3</div>
    <div class="sf-placeholder">
      <div class="sf-icon">📸</div>
      <div class="sf-title">Screenshot: Dispatch Modal</div>
      <div class="sf-desc">The job dispatch form showing all input fields</div>
    </div>
  </div>

  <div class="annotation-legend" id="ann-legend-dispatch">
    <div class="annotation-legend-item" data-for="1">
      <div class="annotation-legend-num">1</div>
      <span><strong>Script field</strong> — paste your Python, Bash, or PowerShell script here</span>
    </div>
    <div class="annotation-legend-item" data-for="2">
      <div class="annotation-legend-num">2</div>
      <span><strong>Capability requirements</strong> — tag filters for which nodes can accept this job</span>
    </div>
    <div class="annotation-legend-item" data-for="3">
      <div class="annotation-legend-num">3</div>
      <span><strong>Sign & Submit</strong> — signs the script with your registered key before dispatching</span>
    </div>
  </div>
</div>
```

**JS — highlight corresponding legend item when hovering annotation:**
```javascript
document.querySelectorAll('.annotation').forEach(ann => {
  const id = ann.dataset.ann;
  ann.addEventListener('mouseenter', () => {
    document.querySelectorAll(`[data-for="${id}"]`).forEach(item => {
      item.style.background = 'var(--color-accent-light)';
      item.style.borderRadius = 'var(--radius-sm)';
      item.style.padding = '4px 8px';
    });
  });
  ann.addEventListener('mouseleave', () => {
    document.querySelectorAll(`[data-for="${id}"]`).forEach(item => {
      item.style.background = '';
      item.style.padding = '';
    });
  });
});
```

---

## GIF Player

See `design-system.md` for CSS. Minimal JS implementation:

```javascript
window.playGif = function(player) {
  const img = player.querySelector('img');
  const overlay = player.querySelector('.gif-overlay');
  if (!img) return;
  // Restart GIF by re-assigning src
  const src = img.src;
  img.src = '';
  img.src = src;
  img.style.display = 'block';
  overlay.classList.add('hidden');
};

// Click anywhere on playing GIF to pause (reload the overlay)
document.querySelectorAll('.gif-player:not(.placeholder)').forEach(player => {
  player.addEventListener('click', function() {
    const overlay = this.querySelector('.gif-overlay');
    if (overlay.classList.contains('hidden')) {
      // "Pause" — show overlay again (GIF itself pauses via display:none)
      const img = this.querySelector('img');
      if (img) img.style.display = 'none';
      overlay.classList.remove('hidden');
    } else {
      playGif(this);
    }
  });
});
```

---

## Before/After Screenshot Comparison

Two-column layout for showing UI state before and after an action.

**HTML:**
```html
<div class="before-after">
  <div class="ba-panel">
    <div class="ba-label ba-label--before">Before</div>
    <div class="screenshot-frame" style="--sh: 200px">
      <div class="sf-placeholder">
        <div class="sf-icon">📸</div>
        <div class="sf-title">Job status: PENDING</div>
        <div class="sf-desc">The job row showing amber PENDING badge</div>
      </div>
    </div>
    <p class="ba-caption">Job sitting in the queue, waiting for a node to pick it up</p>
  </div>
  <div class="ba-arrow">→</div>
  <div class="ba-panel">
    <div class="ba-label ba-label--after">After</div>
    <div class="screenshot-frame" style="--sh: 200px">
      <div class="sf-placeholder">
        <div class="sf-icon">📸</div>
        <div class="sf-title">Job status: COMPLETED</div>
        <div class="sf-desc">The job row showing green COMPLETED badge with output visible</div>
      </div>
    </div>
    <p class="ba-caption">Job completed — green badge, output available in the drawer</p>
  </div>
</div>
```

**CSS:**
```css
.before-after {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: var(--space-4);
  align-items: center;
  margin: var(--space-6) 0;
}

.ba-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 700;
  margin-bottom: var(--space-2);
}
.ba-label--before { color: var(--color-text-muted); }
.ba-label--after  { color: var(--color-success); }

.ba-arrow {
  font-size: 1.5rem;
  color: var(--color-accent);
  text-align: center;
}

.ba-caption {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin: var(--space-2) 0 0;
}

@media (max-width: 600px) {
  .before-after { grid-template-columns: 1fr; }
  .ba-arrow { transform: rotate(90deg); }
}
```

---

## Workflow Scenario Quiz

Same structure as `codebase-to-course` multiple-choice quizzes but questions are **workflow-based** ("what do you do?") not knowledge-based.

**HTML (same pattern, operator-flavoured questions):**
```html
<div class="quiz-container">
  <div class="quiz-q" data-correct="b">
    <div class="scenario-box">
      <span class="scenario-label">Scenario</span>
      A job has been PENDING for 15 minutes. All nodes show as ONLINE. What do you check first?
    </div>
    <div class="quiz-options">
      <button class="quiz-option" data-val="a" onclick="selectOpt(this)">
        <div class="quiz-option-radio"></div>
        <span>Restart all nodes</span>
      </button>
      <button class="quiz-option" data-val="b" onclick="selectOpt(this)">
        <div class="quiz-option-radio"></div>
        <span>Check the job's capability requirements against what the online nodes report — there may be a mismatch</span>
      </button>
      <button class="quiz-option" data-val="c" onclick="selectOpt(this)">
        <div class="quiz-option-radio"></div>
        <span>Delete and re-create the job</span>
      </button>
    </div>
    <div class="quiz-feedback" id="q1-feedback"></div>
  </div>

  <div class="quiz-actions">
    <button class="btn btn-primary" onclick="checkQuiz('quiz-section-id')">Check Answers</button>
    <button class="btn btn-secondary" onclick="resetQuiz('quiz-section-id')">Try Again</button>
  </div>
</div>
```

**Quiz JS (same as codebase-to-course — reuse that implementation verbatim).**

---

## Callout Boxes

Three operator-specific types (same HTML structure, different class):

```html
<!-- TIP: faster paths, keyboard shortcuts, power-user tricks -->
<div class="callout callout-tip">
  <div class="callout-icon">💡</div>
  <div class="callout-content">
    <span class="callout-title">Pro tip</span>
    <p>You can bulk-cancel multiple PENDING jobs by selecting them with the checkbox column, then using the Actions menu at the top of the list.</p>
  </div>
</div>

<!-- WARNING: actions with non-obvious consequences -->
<div class="callout callout-warning">
  <div class="callout-icon">⚠️</div>
  <div class="callout-content">
    <span class="callout-title">Watch out</span>
    <p>Changing a node's tags while it has ASSIGNED jobs may cause those jobs to stall. Drain the node first (wait for active jobs to complete) before editing its configuration.</p>
  </div>
</div>

<!-- DANGER: irreversible or destructive actions -->
<div class="callout callout-danger">
  <div class="callout-icon">🚫</div>
  <div class="callout-content">
    <span class="callout-title">Irreversible</span>
    <p>Revoking a node certificate cannot be undone. The node will need to be re-enrolled with a new JOIN_TOKEN before it can receive work again.</p>
  </div>
</div>
```

---

## Status Flow Diagram

Shows how a job moves through statuses with visual state machine.

**HTML:**
```html
<div class="status-flow">
  <div class="sf-state sf-state--start">
    <span class="status-badge status-pending">PENDING</span>
    <p>Waiting for a node</p>
  </div>
  <div class="sf-arrow sf-arrow--success">→<span>Node picks up</span></div>
  <div class="sf-state">
    <span class="status-badge status-running">ASSIGNED</span>
    <p>Node is executing</p>
  </div>
  <div class="sf-split">
    <div class="sf-path">
      <div class="sf-arrow sf-arrow--success">↓<span>Exit 0</span></div>
      <div class="sf-state sf-state--end">
        <span class="status-badge status-complete">COMPLETED</span>
        <p>Output available</p>
      </div>
    </div>
    <div class="sf-path">
      <div class="sf-arrow sf-arrow--error">↓<span>Exit ≠ 0</span></div>
      <div class="sf-state sf-state--end">
        <span class="status-badge status-failed">FAILED</span>
        <p>Check error output</p>
      </div>
    </div>
  </div>
</div>
```

**CSS:**
```css
.status-flow {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  box-shadow: var(--shadow-sm);
  margin: var(--space-6) 0;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.sf-state {
  display: flex; flex-direction: column; align-items: center;
  gap: var(--space-2); text-align: center;
  padding: var(--space-3);
}

.sf-state p {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin: 0;
}

.sf-arrow {
  display: flex; flex-direction: column; align-items: center;
  font-size: 1.2rem; gap: 2px;
}
.sf-arrow span {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
}
.sf-arrow--success { color: var(--color-success); }
.sf-arrow--error   { color: var(--color-error); }

.sf-split { display: flex; gap: var(--space-4); }
.sf-path { display: flex; flex-direction: column; align-items: center; }
```

---

## Keyboard Shortcut Reference

Scannable table of all shortcuts, typically placed in a "Power Features" module.

**HTML:**
```html
<div class="shortcut-table">
  <div class="shortcut-row shortcut-header">
    <span>Action</span>
    <span>Shortcut</span>
  </div>
  <div class="shortcut-row">
    <span>Open dispatch form</span>
    <span class="kbd"><span class="key">Ctrl</span><span class="key">Shift</span><span class="key">D</span></span>
  </div>
  <div class="shortcut-row">
    <span>Refresh job list</span>
    <span class="kbd"><span class="key">R</span></span>
  </div>
  <div class="shortcut-row">
    <span>Navigate between sections</span>
    <span class="kbd"><span class="key">↑</span><span class="key">↓</span></span>
  </div>
</div>
```

**CSS:**
```css
.shortcut-table {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border-light);
  margin: var(--space-4) 0;
}
.shortcut-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--color-border-light);
  font-size: var(--text-sm);
}
.shortcut-row:last-child { border-bottom: none; }
.shortcut-header {
  background: var(--color-bg-warm);
  font-weight: 600;
  font-family: var(--font-display);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-text-muted);
}
.shortcut-row:not(.shortcut-header):hover {
  background: var(--color-accent-light);
}
```

---

## Glossary Tooltips

**Identical implementation to `codebase-to-course`.** Use `position: fixed` tooltips appended to `document.body` to prevent clipping by `overflow: hidden` ancestor containers.

```html
<!-- Mark up operator-specific terms inline -->
<p>
  Each <span class="term" data-definition="A node is a machine (physical or virtual) that has the puppet agent installed. It polls the Puppeteer server for jobs and executes them. Nodes can run anywhere — your laptop, a server, a cloud VM.">node</span>
  reports its capabilities every 30 seconds via the heartbeat system.
</p>
```

**Operator-guide tooltip focus:** Tooltip every product concept, status value, and acronym on first use per module. Unlike the developer course, you don't need to explain programming concepts — focus on product-specific vocabulary your operators might not know yet.

See `codebase-to-course/references/interactive-elements.md` for the complete tooltip JS implementation — reuse it verbatim.

---

## Feature/Section Cards

Icon + name + one-line description cards. Use for the orientation module ("here are all the sections in the dashboard").

```html
<div class="feature-cards">
  <div class="feature-card">
    <div class="fc-icon" style="background:var(--color-actor-1)">📊</div>
    <div>
      <strong class="fc-name">Dashboard</strong>
      <p class="fc-desc">Live summary: active nodes, recent jobs, system health</p>
    </div>
  </div>
  <div class="feature-card">
    <div class="fc-icon" style="background:var(--color-actor-2)">⚡</div>
    <div>
      <strong class="fc-name">Jobs</strong>
      <p class="fc-desc">Dispatch scripts, monitor status, view output and audit trail</p>
    </div>
  </div>
</div>
```

```css
.feature-cards { display: flex; flex-direction: column; gap: var(--space-3); }
.feature-card {
  display: flex; align-items: center; gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--duration-fast), transform var(--duration-fast);
  cursor: default;
}
.feature-card:hover { box-shadow: var(--shadow-md); transform: translateX(4px); }
.fc-icon {
  width: 44px; height: 44px; border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.2rem; flex-shrink: 0;
}
.fc-name { display: block; font-weight: 600; color: var(--color-text); font-size: var(--text-base); }
.fc-desc { font-size: var(--text-sm); color: var(--color-text-secondary); margin: 2px 0 0; }
```

---

## Tabbed Procedure Switcher

For the same task with different paths (e.g., "Dispatch via UI" vs "Dispatch via API"). Operator guides often need this for power users.

**HTML:**
```html
<div class="tab-switch" data-group="dispatch-method">
  <div class="tab-switch-tabs">
    <button class="ts-tab active" onclick="switchTab('dispatch-method', 'ui')">Via Dashboard</button>
    <button class="ts-tab" onclick="switchTab('dispatch-method', 'api')">Via API</button>
  </div>
  <div class="ts-panel" data-tab="dispatch-method-ui" style="display:block">
    <!-- step guide for UI approach -->
  </div>
  <div class="ts-panel" data-tab="dispatch-method-api" style="display:none">
    <!-- step guide for API approach -->
  </div>
</div>
```

**JS:**
```javascript
window.switchTab = function(group, tab) {
  document.querySelectorAll(`[data-group="${group}"] .ts-tab`).forEach(t => {
    t.classList.toggle('active', t.textContent.toLowerCase().includes(tab));
  });
  document.querySelectorAll(`[data-tab^="${group}-"]`).forEach(p => {
    p.style.display = p.dataset.tab === `${group}-${tab}` ? 'block' : 'none';
  });
};
```

**CSS:**
```css
.tab-switch { margin: var(--space-6) 0; }
.tab-switch-tabs {
  display: flex; gap: 2px;
  border-bottom: 2px solid var(--color-border);
  margin-bottom: var(--space-4);
}
.ts-tab {
  padding: var(--space-2) var(--space-5);
  border: none; background: transparent;
  font-family: var(--font-body); font-size: var(--text-sm); font-weight: 500;
  color: var(--color-text-muted); cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color var(--duration-fast), border-color var(--duration-fast);
}
.ts-tab:hover { color: var(--color-text); }
.ts-tab.active { color: var(--color-accent); border-bottom-color: var(--color-accent); }
```

---

## Progress Checklist

Interactive checklist for multi-step setup processes (e.g., "First-Time Setup Checklist"). Persists state in `localStorage`.

**HTML:**
```html
<div class="progress-checklist" id="setup-checklist">
  <div class="pcl-header">
    <span class="pcl-title">First-Time Setup</span>
    <span class="pcl-count" id="pcl-count">0 / 4 complete</span>
  </div>
  <label class="pcl-item">
    <input type="checkbox" data-key="setup-1" onchange="updateChecklist('setup-checklist')">
    <span class="pcl-check"></span>
    <span>Add your first node using a JOIN_TOKEN</span>
  </label>
  <label class="pcl-item">
    <input type="checkbox" data-key="setup-2" onchange="updateChecklist('setup-checklist')">
    <span class="pcl-check"></span>
    <span>Upload a signing key in Signatures</span>
  </label>
  <label class="pcl-item">
    <input type="checkbox" data-key="setup-3" onchange="updateChecklist('setup-checklist')">
    <span class="pcl-check"></span>
    <span>Dispatch your first test job</span>
  </label>
  <label class="pcl-item">
    <input type="checkbox" data-key="setup-4" onchange="updateChecklist('setup-checklist')">
    <span class="pcl-check"></span>
    <span>Invite a team member and assign them the Operator role</span>
  </label>
</div>
```

**CSS:**
```css
.progress-checklist {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-light);
  margin: var(--space-6) 0;
}
.pcl-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-4); }
.pcl-title { font-family: var(--font-display); font-weight: 600; }
.pcl-count { font-size: var(--text-sm); color: var(--color-text-muted); font-family: var(--font-mono); }
.pcl-item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) 0; cursor: pointer;
  font-size: var(--text-sm); color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border-light);
}
.pcl-item:last-child { border-bottom: none; }
.pcl-item input[type="checkbox"] { display: none; }
.pcl-check {
  width: 20px; height: 20px; border-radius: 50%;
  border: 2px solid var(--color-border);
  flex-shrink: 0;
  transition: all var(--duration-fast);
}
.pcl-item input:checked ~ .pcl-check {
  background: var(--color-success);
  border-color: var(--color-success);
}
.pcl-item input:checked ~ span:last-child {
  text-decoration: line-through;
  color: var(--color-text-muted);
}
```

**JS:**
```javascript
window.updateChecklist = function(id) {
  const checklist = document.getElementById(id);
  const items = checklist.querySelectorAll('input[type="checkbox"]');
  let completed = 0;
  items.forEach(item => {
    if (item.checked) { completed++; }
    // Persist
    localStorage.setItem(`checklist-${item.dataset.key}`, item.checked ? '1' : '0');
  });
  const count = checklist.querySelector('.pcl-count');
  if (count) count.textContent = `${completed} / ${items.length} complete`;
};

// Restore from localStorage on load
document.querySelectorAll('.progress-checklist').forEach(checklist => {
  checklist.querySelectorAll('input[type="checkbox"]').forEach(item => {
    if (localStorage.getItem(`checklist-${item.dataset.key}`) === '1') {
      item.checked = true;
    }
  });
  updateChecklist(checklist.id);
});
```
