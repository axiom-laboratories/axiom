# PRD: Advanced Foundry & Blueprint Composition (v2.0)

## 1. Executive Summary
The Master of Puppets (MoP) Foundry is the internal factory for creating immutable, stateless 'Puppet' container images. This document outlines the transition from a manual CRUD-based blueprint system to an intelligent, compatibility-aware composition engine. The goal is to allow Administrators to 'bake' complex environments (Runtimes) and secure network perimeters (Networks) into Puppet images with minimal friction, ensuring OS-level compatibility and support for custom software supply chains.

## 2. Core Objectives
- **Modularity**: Maintain the strict separation between 'What' (Runtime) and 'Where' (Network).
- **Compatibility Intelligence**: Prevent the selection of incompatible tools or packages for a given Base OS.
- **Supply Chain Control**: Enable the use of official OS repositories and custom internal/private repositories (APT, PyPI, etc.).
- **Admin Efficiency**: Provide a 'Wizard' experience for image composition that reduces manual Dockerfile/JSON editing.

## 3. Functional Requirements

### 3.1 The 'Smelter' Registry (Approved Ingredients)
- **Vetted Ingredient Catalog**: A centralized registry of approved Python packages (PIPs), system binaries, and tools.
- **Attributes**: Each entry includes `package_name`, `version_constraint`, `sha256_hash`, `os_family`, and `approval_date`.
- **Enforcement Mode**: 
    - **STRICT**: The Smelter will fail any build containing 'Unapproved' ingredients.
    - **WARNING**: Build succeeds but flags the Puppet image as 'Non-Compliant' in the dashboard.
- **Auto-Vetting**: Integration with security scanners (e.g., Safety, Bandit) to automatically flag packages with known CVEs in the registry.

### 3.2 Compatibility-Aware Runtime Composition
- **OS Family Filtering**: The system must categorize all tools and recipes by `OS_FAMILY` (e.g., DEBIAN, ALPINE, WINDOWS_NANO).
- **Runtime Dependency Mapping**: Tools in the `CapabilityMatrix` should optionally declare a required runtime (e.g., 'Scapy' requires 'Python 3.x').
- **Validation Logic**: The Foundry API must reject any Blueprint where a tool's `OS_FAMILY` does not match the `Base OS` of the blueprint.

### 3.2 Advanced Package Management ('Pre-baking')
- **Native OS Packages**: Admins can select packages directly from the official OS repositories (e.g., `nmap`, `tcpdump`, `jq`).
- **Python/PIP Integration**: Direct support for 'pre-baking' PIP packages into the image to reduce node-side startup time.
- **Global Pre-requisites**: Ability to define a 'Core' set of packages that are automatically injected into every Puppet image (e.g., security agents, monitoring hooks).

### 3.3 Custom Repository & Artifact Support
- **Apt/Apk Repositories**: Support for adding custom `.list` files and GPG keys during the 'baking' process.
- **Private PyPI/Index**: Support for `--index-url` and `--trusted-host` for internal Python package mirrors.
- **Repo Presets**: Admins can define 'Corporate Repos' once in system settings and toggle them on/off for individual blueprints.
- **Artifact 'Staging Area'**: A UI/API staging zone for one-off binaries or proprietary `.so` libraries. The Smelter automatically generates `COPY` instructions to inject these into specific paths (e.g., `/usr/local/lib`) during the build.

### 3.4 The Foundry Wizard (UI)
- **Step-based Workflow**:
  1. **Base Selection**: Pick an 'Approved OS' image.
  2. **Runtime Setup**: Select compatible runtimes (Python, Node, Go).
  3. **Tool/Stack Selection**: Toggle compatible tools from the filtered Capability Matrix.
  4. **Package Injection**: Search/Add native OS packages and PIP requirements.
  5. **Repository Config**: Select from Repo Presets or add ad-hoc sources.

### 3.5 Validation & Assurance (MANDATORY)
- **The 'Smelt-Check' (Dry-Run Validator)**: Before an image is tagged/pushed, the Smelter MUST spawn a ephemeral container from the new image and execute the `validation_cmd` for every included tool. Any exit code != 0 aborts the build.

### 3.6 Enhanced Capabilities (Nice-to-Have / Phase 2)
- **Multi-Arch Smelting**: Support for `linux/amd64` and `linux/arm64` cross-builds via `buildx` for diverse node hardware.
- **Pre-emptive Caching ('Warm-up')**: Ability to define 'Warm-up' commands (e.g., `import pandas`) that run at build time to prime JIT/Caches for faster Puppet startup.
- **Foundry 'Pulse' (Auto-Smelt)**: Scheduled or Webhook-triggered monitoring of upstream Base OS images (e.g., DockerHub) to trigger automatic re-builds on security patches.
- **Layer Optimization**: Automatic 'squashing' of Docker layers and multi-stage builds to strip build-time dependencies (compilers/headers) from the final production Puppet image.

## 4. Technical Architecture

### 4.1 Database Schema Updates (The Smelter Core)
- **`approved_ingredients`**: New table for storing vetted packages (Name, Version, Hash, OS Family, Approval Status).
- **`capability_matrix`**: Add `requires_runtime` (String, Nullable) and `os_family` (String, Mandatory).
- **`approved_os`**: Add `default_package_manager` (APT, APK, etc.) and `os_version` metadata.
- **`blueprint_definitions`**: Update JSON schema to include:
  ```json
  {
    "system_packages": [],
    "python_packages": [],
    "custom_repositories": [
      { "type": "apt", "url": "...", "key": "..." }
    ]
  }
  ```

### 4.2 Foundry Service Build Logic (Deterministic Layering)
- To maximize Docker layer caching and build speed, the Smelter MUST generate the Dockerfile using a deterministic sequence:
  1. **Layer 0**: `FROM {base_os}`
  2. **Layer 1**: `ARG` and `ENV` for Smelt-Time Environment Variables.
  3. **Layer 2**: Setup Custom Repositories and GPG Keys.
  4. **Layer 3**: Install System Packages (OS-native).
  5. **Layer 4**: Install Runtimes (Python, Node, Go).
  6. **Layer 5**: Inject Artifacts (via Staging Area `COPY`).
  7. **Layer 6**: Install Approved Ingredients (PIPs/Binaries).
  8. **Layer 7**: **Identity Injection**: Bake `/etc/puppet_metadata.json` containing `template_id`, `canonical_id`, `version`, and `build_timestamp`.
  9. **Layer 8**: Inject MoP Core (environment_service).

## 5. Security & Governance
- **Admin-Only Access**: Only users with `foundry:write` (Admins) can compose or build images.
- **Immutable Tagging**: Images are tagged with a content-addressable hash (`canonical_id`) to prevent tampering.
- **Signature Verification**: (Future) Enable signing of the final baked image before it is pushed to the internal registry.
- **Smelter Attestation (SLSA)**: At build completion, the Smelter MUST generate and sign a 'Provenance Document' using the Control Plane's private key. This document lists all ingredients and their hashes, allowing remote nodes to cryptographically verify that an image was indeed smelted by the authorized Foundry.
- **Build-Time Secret Mounting**: Support for passing credentials (e.g., private git tokens, artifactory keys) to the Smelter via `docker build --secret` to ensure they are never committed to the image history or layers.
- **Smelter Egress Control**: Enforce network isolation during the `docker build` phase itself to prevent malicious `curl` or `pip` scripts from exfiltrating data or fetching unapproved secondary payloads during image creation.
- **Smelter Resource Isolation**: Enforce strict CPU and memory limits on the Smelter process (e.g., max 4GB RAM per build) to protect the host Puppeteer Control Plane from resource starvation during heavy builds.
- **Provenance & Attribution**: Link every Smelt operation to an Audit Event containing the Admin's ID and an optional justification/ticket number.

## 6. Lifecycle & Operations
- **The Image Bill of Materials (BOM)**: The Smelter must generate a JSON manifest detailing every OS package, PIP package, tool, and repository injected into the image. This BOM is stored in the DB and visible in the Dashboard for compliance auditing.
- **Puppet Image Lifecycle Management**:
    - **ACTIVE**: Image is available for use.
    - **DEPRECATED**: Image can be used by existing nodes, but triggers a warning in the UI/Logs.
    - **REVOKED**: Puppeteer forcefully refuses to schedule jobs to nodes running this image version.
- **Air-Gapped Smelting (Offline Export)**: Support for exporting a fully baked Puppet image and its dependencies as an encrypted tarball for deployment into strictly air-gapped environments without external registry access.

--- 
*Last Updated: 2026-03-09*
