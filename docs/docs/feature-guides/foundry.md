# Foundry

Foundry builds custom Docker images for Axiom Nodes. Instead of using a generic base image, you define exactly what packages, tools, and network configuration each node image should contain — then Foundry assembles and builds it.

The workflow has two stages: first you create **blueprints** that define runtime or network configuration, then you compose those blueprints into a **template** that Foundry turns into a Docker image. Nodes enroll against a template, so every node launched from the same template has an identical, reproducible environment.

---

!!! enterprise

## Concepts

| Concept | Description |
|---------|-------------|
| Blueprint | Reusable definition of a runtime environment (Python packages) or network configuration |
| Template | Combines one RUNTIME blueprint and one NETWORK blueprint into a Docker image build |
| Smelter | Built-in package scanner that validates blueprint ingredients against the Smelter registry |
| Image Lifecycle | Status tracking for built templates: ACTIVE, DEPRECATED, or REVOKED |

---

## Blueprints

Blueprints come in two types:

- **RUNTIME** — defines the Python packages and execution environment that will be available inside the node container
- **NETWORK** — defines network configuration and connectivity settings for the node

### Creating a blueprint

Navigate to **Foundry → Blueprints → New Blueprint**. The Blueprint Wizard opens and walks you through five steps:

**Step 1 — Identity**

Choose a name, select the blueprint type (RUNTIME or NETWORK), and choose the OS family (DEBIAN, ALPINE, or FEDORA). If you want to base the new blueprint on an existing one, use the **Clone Existing** option — it pre-populates all fields from the selected blueprint and lets you modify from there.

**Step 2 — Base Image**

Select the base container image for the blueprint. This is the Docker image that Foundry will build on top of.

**Step 3 — Ingredients**

Add the Python packages to include. This is where Smelter runs its validation (see [Smelter](#smelter) below).

!!! danger "Package format"
    Packages **must** be specified as a dict with a `"python"` key:

    ```json
    {"python": ["requests", "numpy", "pandas"]}
    ```

    A plain list like `["requests", "numpy"]` is rejected. This is the most common source of blueprint creation failures — if your blueprint is not saving, check the package format first.

**Step 4 — Tools**

Select the capability tools to inject into the node image. These are pre-built additions (such as file transfer utilities or monitoring agents) that extend what the node can do.

**Step 5 — Review**

The wizard shows a JSON preview of the full blueprint definition. Confirm the details and click **Submit**.

### Advanced mode

The wizard has an **Advanced (JSON)** toggle that bypasses the guided form and lets you paste raw JSON directly. This is useful for importing a blueprint exported from another environment or for making bulk edits without stepping through each page.

After submission, the blueprint appears in the Blueprints list showing its OS family, type, and package count.

---

## Templates

A template combines one RUNTIME blueprint and one NETWORK blueprint into a single Docker image build.

### Building a template

Navigate to **Foundry → Templates → New Template**.

1. Give the template a name
2. Select the RUNTIME blueprint to use
3. Select the NETWORK blueprint to use
4. Click **Build**

Foundry copies the `environment_service` code into a temporary build context, generates a Dockerfile from the blueprint definitions, and runs `docker build`. Build progress is visible in the dashboard; if the build fails, the Docker build log is surfaced so you can diagnose the issue.

On success, the template shows a **Last Built** timestamp and is ready for node enrollment.

### Rebuilding after a base image update

If the underlying base image changes (for example, after a security patch), navigate to **Foundry → Templates**, find the template row, and click **Rebuild**. Foundry will re-run the Docker build using the current blueprint definitions and the updated base image.

---

## Smelter

Smelter is the built-in package validation engine. It runs during blueprint creation at **Step 3 (Ingredients)** and checks each package against the Smelter registry for known CVEs.

Smelter has two enforcement modes:

| Mode | Behaviour |
|------|-----------|
| STRICT | Build fails if any package fails the CVE scan — the blueprint cannot be saved until the offending package is removed or replaced |
| WARNING | Build proceeds normally; the template shows an amber warning badge indicating that one or more packages have flagged vulnerabilities |

The enforcement mode is configured per-template at build time.

!!! info "Deep CVE configuration"
    Configuring custom enforcement policies and adding packages to the Smelter allow-list is covered in the [Security](../security/index.md) section.

---

## Image Lifecycle

Every built template has a lifecycle status. Use **Foundry → Templates** to view and change the status of any template.

| Status | Meaning | How to change |
|--------|---------|---------------|
| ACTIVE | Normal operation — nodes can enroll and the image is in active use | Default state after a successful build |
| DEPRECATED | New node enrollments with this template are blocked; nodes that already hold a cert from this template continue to function | Click **Deprecate** in the template row |
| REVOKED | All enrollment with this template is blocked (403 returned at `/api/enroll`) | Click **Revoke** in the template row |

!!! warning "Revoke is irreversible"
    Revoking a template cannot be undone from the dashboard. If you want to phase out a template without immediately blocking all nodes, use **DEPRECATED** first. DEPRECATED allows existing nodes to keep running while preventing new enrollments — giving you time to migrate before revoking.

For the enforcement mechanics that explain how REVOKED blocks the `/api/enroll` endpoint, see the [Architecture guide](../developer/architecture.md).

---

## Quick Reference

| Action | Steps |
|--------|-------|
| Create a blueprint | Foundry → Blueprints → New Blueprint → complete the wizard |
| Build a template | Foundry → Templates → New Template → select blueprints → Build |
| Rebuild after base image update | Foundry → Templates → template row → Rebuild |
| Change lifecycle status | Foundry → Templates → template row → status dropdown |
