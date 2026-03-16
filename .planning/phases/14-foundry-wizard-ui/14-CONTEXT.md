# Phase 14 Context: Blueprint Composition Wizard

## Goal
Replace the raw JSON blueprint editor with a guided, multi-step UI that ensures safety and provided high helpfulness. The wizard integrates Smelter Registry status, Compatibility Matrix metadata, and automated dependency resolution to ensure blueprints are valid before they ever hit the Foundry.

## Decisions

### 1. Wizard Structure & Steps
- **Clone Support**: Users can start fresh or clone from an existing blueprint template.
- **Informative Base Selection**: The image selection step will show "Last Updated" and "Compliance" metadata for approved OS images.
- **Registry Transparency**: Ingredient search results will display real-time `mirror_status` and `is_vulnerable` flags.
- **Strict Compatibility**: Only tools marked as compatible with the selected OS Family will be displayed in the Tool selection step.

### 2. Interaction & "High Helpfulness" Logic
- **Auto-Dependency Injection**: Selecting a Tool with `runtime_dependencies` will automatically add those packages to the ingredients list, accompanied by a UI notification.
- **Permissive but Informed**: Users can select `PENDING` or `VULNERABLE` ingredients, but the wizard will display explicit warnings about build failure risks and security vulnerabilities.
- **Real-time Diffing**: The final "Review" step will show a side-by-side JSON diff when editing or cloning, highlighting exactly what changed.

### 3. Editor Co-existence & Governance
- **Wizard First**: The primary "Create Blueprint" path is the Wizard.
- **Advanced Escape Hatch**: A "Raw JSON" editor is available under an "Advanced" toggle. Switching to it midway will convert the current wizard state into JSON.
- **Friction-based Bypass**: The advanced editor allows bypassing Smelter/Matrix validation, but only after an explicit confirmation/friction gate.
- **Draft Persistence**: The wizard supports saving partially completed configurations as "Drafts" for later resumption.

## Code Context
- **Component**: Create `BlueprintWizard.tsx` using a multi-step state machine or dedicated hook.
- **API**: Reuse `/api/smelter/ingredients`, `/api/capability-matrix`, and `/api/approved-os` for data fetching.
- **Drafts**: Leverage the existing `status: DRAFT` field implemented in Phase 17/19.

## Success Criteria
1. User can create a valid blueprint without typing any JSON.
2. Selecting a tool automatically adds required PIP packages.
3. Vulnerable ingredients trigger visible security warnings.
4. Switching from Wizard to Advanced mode preserves all current selections.
