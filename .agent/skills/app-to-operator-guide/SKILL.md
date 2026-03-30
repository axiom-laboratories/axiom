---
name: app-to-operator-guide
description: "Turn any web application into a beautiful, interactive single-page HTML operator guide that teaches non-technical users how to USE the product — not how it's built. Use when someone wants to create an interactive user manual, onboarding guide, feature walkthrough, or operator handbook from an existing application. Also trigger when users mention 'create a user guide', 'make an operator manual', 'interactive documentation for users', 'how-to guide for the app', 'onboarding guide', or 'teach someone how to use this'. Produces a self-contained HTML file with step-by-step task modules, annotated screenshot frames, GIF player placeholders, workflow animations, and scenario-based quizzes."
---

# App-to-Operator Guide

Transform any web application into a stunning, interactive single-page HTML operator guide. The output is a single self-contained HTML file (no dependencies except Google Fonts) that teaches people how to **use** the product through task-based modules, annotated screenshot frames, GIF walkthroughs, and practical scenario quizzes.

## How This Differs from `codebase-to-course`

| Dimension | codebase-to-course | app-to-operator-guide |
|---|---|---|
| **Target learner** | Vibe coder learning how the code works | Operator/user learning how to do their job |
| **Curriculum arc** | Concept-first (what exists) → code details | Task-first (what to do) → edge cases |
| **Core teaching element** | Code ↔ English translation | Annotated screenshot + step-by-step click guide |
| **Media** | Code blocks only | Screenshots, GIFs, annotated UI overlays |
| **Quizzes** | Architecture + debugging scenarios | Workflow scenarios ("what do you click to...?") |
| **Metaphors** | Explain technical concepts | Not needed — tasks speak for themselves |
| **Module structure** | Concept per module | **Task** per module ("How to dispatch a job") |

## Who This Is For

The target learner is a **non-technical operator** — someone who has been given access to the application and needs to get things done with it. They may be a system administrator, an operations analyst, a manager, or a new team member. They are NOT interested in how the code works. They want to know: **what buttons do I click, in what order, to accomplish X?**

**Their goals:**
- Complete their assigned tasks without needing to ask for help
- Understand *why* a workflow works the way it does (so they can adapt when things change)
- Know what to do when something looks wrong
- Become self-sufficient quickly

**Assume they know their domain, not the tool.** They might be an expert sysadmin who has never seen this specific product before. Meet them where they are: "here's how this app thinks about your familiar concept."

---

## The Process (4 Phases)

### Phase 1: UI Analysis

Before writing any guide HTML, understand the application from a **user's perspective**. Read the frontend code (views, routes, components), the README, and any docs. Navigate through the UI mentally.

**What to extract:**
- The main tasks a user needs to accomplish (the "jobs to be done")
- Every major UI section and what it controls
- The key workflows (dispatch a job, add a node, create a user, etc.)
- Common error states and what they mean in plain language
- Any gotchas or non-obvious behaviours (things that trip new users up)
- Keyboard shortcuts, bulk actions, power-user features worth knowing

**Do NOT read deeply into backend logic** — focus on what the user sees and touches. You're writing for the dashboard, not the database.

**Identify where screenshots would go** even if you don't have real ones yet. Mark these clearly with descriptive placeholders.

### Phase 2: Curriculum Design

Structure the guide as **5–8 task-based modules**. Each module answers one question: *"How do I do X?"*

| Module Position | Purpose |
|---|---|
| 1 | Orientation — "Here's the dashboard and what each section is for" |
| 2–5 | Core tasks — one module per major workflow the operator needs daily |
| 6 | Edge cases & errors — "When something looks wrong, here's what to do" |
| 7 (optional) | Power features — shortcuts, bulk actions, advanced settings |

**Module naming convention:** Use action verbs. Not "Jobs" — use "Dispatching and Monitoring Jobs." Not "Nodes" — use "Adding and Managing Nodes."

**Each module should contain:**
- 3–5 screens (sub-sections that scroll within the module)
- At least one annotated screenshot frame or GIF placeholder
- At least one step-by-step click guide
- One tip/warning callout per 2 screens
- A short practical quiz (2–3 scenario questions) at the end of most modules

**Do NOT present the curriculum for approval — just build it.** Design it internally, generate the HTML, and let the user react to the result.

### Phase 3: Build the Guide

Generate a single HTML file with embedded CSS and JavaScript. Read `references/design-system.md` and `references/interactive-elements.md` before writing any markup.

**Build order:**

1. **Foundation** — HTML shell with all module sections (empty), complete CSS system, progress nav, scroll-snap, keyboard navigation, animations.
2. **One module at a time** — Fill content, screenshots, step cards, and interactive elements module by module. Never write all modules in one pass.
3. **Polish pass** — Transitions, mobile responsiveness, visual consistency.

**Critical implementation rules:**
- Self-contained HTML (only external: Google Fonts CDN)
- `scroll-snap-type: y proximity` (not mandatory)
- `min-height: 100dvh` with `100vh` fallback
- Animate only `transform` and `opacity`
- Wrap all JS in IIFE, `passive: true` on scroll listeners
- Touch support for interactive elements, keyboard navigation (arrow keys), ARIA attributes

**Screenshot and GIF handling:**

Screenshots and GIFs cannot be embedded in a self-contained HTML file unless provided as base64 data. Use the following strategy:

1. **If screenshots are provided as base64 or file paths:** Embed directly as `<img>` with `data:image/...` or a relative path.
2. **If no screenshots are provided (most common):** Use CSS **placeholder frames** — styled `<div>` blocks that clearly label what the screenshot shows, with dimensions matching real UI. These look intentional, not broken.
3. **For GIFs:** Use a `<div class="gif-placeholder">` with a play button overlay and description of what the animation demonstrates. Include a "🎥 Record this:" instruction comment in the HTML.

Placeholder frames should be visually polished — they shouldn't look like missing images. Style them as blueprint-sketched UI mockups. See `references/interactive-elements.md` for the exact patterns.

### Phase 4: Review and Open

After generating the guide HTML file, open it in the browser. Walk the user through what was built and invite feedback.

---

## Content Philosophy

### Task-First, Always

Every module opens with a one-sentence answer to "what will I be able to do after this?" Then immediately: the step-by-step. Context and explanation come *after* the task, not before. Operators are busy. Get to the steps.

### Screenshots Are the Primary Teaching Tool

Where `codebase-to-course` uses code↔English translations, this skill uses **annotated screenshots**. Every major step should have a visual. If you don't have a real screenshot, use a polished placeholder frame that clearly labels which UI element the user is looking at.

**Never describe a UI element in prose when you can show it visually.** "Click the blue Dispatch button in the top-right corner" is worse than a screenshot with a numbered annotation on the Dispatch button.

### Step Cards Over Prose

Any procedure longer than 2 steps becomes a **numbered step card sequence** — not a numbered list paragraph. Each step card has: step number, action title, optional screenshot/detail below.

### Scenario Quizzes — Workflow Application

Quizzes test whether the learner can execute a workflow in a new situation:
- ✅ "You need to run a script only on Linux nodes. What field in the dispatch form do you fill in?"
- ✅ "A job shows PENDING for 10 minutes. What's the most likely cause?"
- ❌ "What does JWT stand for?"
- ❌ "Which file handles job assignment?"

### Tips, Warnings, Power-User Callouts

Three callout types:
- **Tip** (accent colour): "Faster way to do this" / keyboard shortcuts / power-user tricks
- **Warning** (amber): "If you do X, Y will happen — be careful"
- **Danger** (red): "This action is irreversible" / destructive operations

### Glossary Tooltips — Product-Specific Terms

Tooltip every product-specific term on first use per module. In an operator guide this means:
- Product concepts (node, job definition, blueprint, signing key, JOIN_TOKEN)
- Status values (PENDING, ASSIGNED, COMPLETED, REVOKED)
- Any acronym: mTLS, RBAC, JWT, CSV, API
- UI region names the user needs to navigate to

Same implementation as `codebase-to-course`: `position: fixed` tooltips appended to `document.body`, never clipped by `overflow: hidden` ancestors.

---

## Gotchas — Common Failure Points

### Placeholder Frames Look Broken
If a placeholder frame looks like a missing image (broken icon, white space), it destroys trust. Style them as intentional UI sketches — grey background, dashed border, text describing what the screenshot shows. See reference for exact CSS.

### Step Lists vs Step Cards
Using `<ol>` numbered lists instead of step cards. Step cards are visually superior for procedures — each step is a card with breathing room, not a run-on list. Always use `<div class="step-cards">`.

### Quiz Questions Test Recall
Asking what a term means instead of testing whether they can execute a workflow. Every quiz question should present a real scenario and ask what the user would DO.

### Too Much Prose Before the Steps
Writing 2–3 paragraphs of context before showing the steps. Operators skip intros. Lead with the steps, add context below.

### Tooltip Clipping (same as codebase-to-course)
Tooltips inside `overflow: hidden` containers (like step cards, translation blocks) get clipped if they use `position: absolute`. Always use `position: fixed` with `getBoundingClientRect()` positioning, appended to `document.body`.

### Module Quality Degradation
Trying to write all modules in one pass causes later modules to be thin. Build one module, verify it in the browser, then continue.

### Missing Screenshots Treated as Failure
Guides built without real screenshots are still fully functional and professional-looking if placeholder frames are styled correctly. Don't apologise for missing screenshots — the placeholders communicate the guide structure and content intent clearly.

---

## Reference Files

- **`references/design-system.md`** — Complete CSS tokens adapted for operator guides. Includes screenshot frame styles, GIF player, annotation overlay system, keyboard shortcut badges.
- **`references/interactive-elements.md`** — Implementation patterns for: annotated screenshot frames, GIF players, step-by-step click guides, before/after comparisons, keyboard shortcut display, scenario quizzes, callout boxes, warning/danger banners.
