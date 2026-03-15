# Phase 13 Context: Package & Repository Mirroring

## Goal
Establish local, high-availability mirrors for Python (PyPI) and System (APT) packages. This ensures that the Foundry build process remains completely isolated from the internet (air-gapped support) and uses only vetted, locally-stored ingredients.

## Decisions

### 1. Mirroring Strategy & UX
- **Automatic Sync**: The system will automatically attempt to mirror a package as soon as it is added to the Smelter Catalog.
- **Air-Gapped Ingestion**: The dashboard will support direct file uploads (`.whl`, `.deb`) for environments without internet access.
- **Status Tracking**: The `approved_ingredients` table will be extended to track `mirror_status` (`PENDING`, `MIRRORED`, `FAILED`).
- **Soft-Purge Retention**: Deleting an ingredient from the active catalog will disable it for builds (sets `is_active=False`) but keep the physical files in the mirror for future use/audit. The delete endpoint must never hard-delete the DB row or remove files from `MIRROR_DATA_PATH`.

### 2. Mirror Enforcement Policy
- **Strict Build Isolation**: A global `FORCE_LOCAL_MIRRORS` policy will be implemented. Docker/Podman builds will be configured to ONLY use the local `pypiserver` and APT repo.
- **Fail-Fast Behavior**: If a build requires an ingredient that is in the active catalog (`is_active=True`) and has not been successfully mirrored (`PENDING` or `FAILED`), the build will fail immediately with HTTP 403. Soft-deleted ingredients (`is_active=False`) are excluded from builds silently — they do not trigger a 403.
- **No Overrides**: The mirroring policy is absolute; no template-level bypasses are permitted.

### 3. Repository Visibility & Observability
- **Health Monitoring**: A "Repo Health" card in the Admin UI will display disk usage and the heartbeat/uptime of mirroring sidecars.
- **Raw File Browser**: Admins can browse the raw file structure of the hosted repositories via a link to the Caddy server on port 8081.
- **Sync Logs**: Raw output from `pip download` and `apt` sync processes will be captured and viewable in the UI for troubleshooting.
- **Source Management**: Upstream mirror sources (e.g., target PyPI indices) will be viewable and configurable via the dashboard using a Config-DB-backed settings panel (`GET`/`PUT /api/admin/mirror-config`).

## Code Context
- **Sidecars**: Implement `pypiserver` and a simple local APT repo (e.g., using `reprepro` or a static file server) as Docker Compose services.
- **Storage**: Use a shared volume (`mirror-data`) accessible by both the sidecars and the `SmelterService`.
- **Foundry Hook**: Update `FoundryService.build_template` to inject `--index-url` (pip) and custom `sources.list` (apt) pointing to the local sidecars.

## Deferred Ideas
The following items were discussed but explicitly deferred from Phase 13:

- **Centralized GPG signing for APT packages**: CONTEXT.md originally locked "Centralized GPG: A single Master Smelter GPG Key will sign all locally hosted APT packages." This has been deferred because:
  1. The local APT mirror is on a controlled internal network. `[trusted=yes]` in `sources.list` is an acceptable simplification when the network path is already trusted.
  2. Full GPG signing would require: key generation and storage, re-running `dpkg-scanpackages` + `gpg --sign` after each package upload, injecting the GPG public key into every Dockerfile, and key rotation tooling. This is significant scope for an internal-only mirror.
  3. If Phase 13 grows to serve as a public or cross-organization mirror, GPG signing should be revisited.
  - Implementation would require: `GET /api/admin/smelter/gpg-key` (expose public key), `apt-ftparchive` or `reprepro` for signed repo generation, and Dockerfile injection of `apt-key add` or a trusted.gpg.d entry.

## Success Criteria
1. Adding an ingredient triggers an automatic download to local storage.
2. An image build succeeds with internet access disabled on the build host.
3. Admin can view real-time sync logs and disk usage in the dashboard.
4. Manual upload of a `.whl` file makes it immediately available for builds.
5. Admin can view and update upstream mirror source URLs from the dashboard.
