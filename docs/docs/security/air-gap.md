# Air-Gap Operation

This guide covers deploying Axiom in a network-isolated environment where internet access is unavailable or restricted.

Axiom is designed with air-gap deployments in mind. The package mirror sidecars and offline documentation plugins allow most of the stack to operate without outbound internet access. This guide documents the full setup, what is already offline-capable, what requires substitution, and how to verify isolation.

For initial setup and deployment context, see [Setup and Deployment](../developer/setup-deployment.md).

---

## What Is Already Offline-Capable

The following components work without internet access after initial setup:

| Component | How it achieves offline capability |
|-----------|-----------------------------------|
| Documentation site | MkDocs `privacy` + `offline` plugins pre-download all external assets (fonts, JavaScript) at Docker build time — zero CDN or outbound requests at runtime |
| Foundry image builds | Python packages sourced from the configured `pypi_mirror_url`; APT packages from `apt_mirror_url` when both mirror URLs are set |
| Smelter CVE scanning | Operates against the mirrored package registry |
| Node execution | Scripts run locally inside containers — the execution runtime makes no outbound calls |
| mTLS enrollment | Node-to-orchestrator mTLS uses the embedded Root CA — no external CA or OCSP required |

---

## Package Mirror Setup

> For a full from-scratch setup guide, see [Package Mirror Runbooks](../runbooks/package-mirrors.md).

The mirror sidecars must be configured and seeded before disconnecting from the internet.

**Step 1: Confirm mirror sidecars are running**

The PyPI mirror and APT mirror sidecars are included in `compose.server.yaml`. Confirm they are running:

```bash
docker compose -f puppeteer/compose.server.yaml ps
```

**Step 2: Configure mirror URLs**

Update the mirror configuration via the API:

```bash
curl -X PATCH \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  https://<HOST>/admin/mirror-config \
  -d '{"pypi_mirror_url": "http://pypi-mirror:3141", "apt_mirror_url": "http://apt-mirror:3142"}'
```

This action is logged as `mirror:config_updated` in the audit log.

**Step 3: Seed the mirrors**

Before disconnecting from the internet, ensure all required packages are present in the mirrors. Use the Smelter to pre-approve and mirror all ingredients your Foundry templates will need:

1. Navigate to **Admin** → **Smelter** → **Approved Ingredients**
2. Add each package your templates require
3. Trigger a mirror sync from the **Mirror Config** panel

**Step 4: Upload packages after isolation**

When a new package is needed after internet access is removed, an admin must upload the package file directly:

- **PyPI packages**: navigate to **Admin** → **Smelter** → **Upload Package** — logs `smelter:package_uploaded`
- **APT packages**: upload the `.deb` file to the APT mirror sidecar via its admin interface

---

## Offline Build Validation

Before fully disconnecting, verify that Foundry builds succeed with the mirror configuration active and no internet access.

**Procedure:**

1. Configure mirror URLs as described above
2. Block outbound internet access at the network or firewall level (or use a Docker network policy)
3. Trigger a Foundry build with `--no-cache` to force all dependencies to be fetched from scratch:
   - Navigate to **Templates** → select a template → click **Build**
4. Confirm the build succeeds — a failure at this stage means a dependency is not yet present in the mirror

!!! tip
    Run this validation before committing to air-gap mode. It is significantly easier to debug missing packages while internet access is still available.

---

## Outbound Network Restrictions

Once mirrors are seeded and validated, apply network isolation.

Recommended firewall rules — allow only:

- Internal LAN traffic between orchestrator, nodes, and mirror sidecars
- Any required on-premises services (internal DNS, LDAP, SIEM)

Block all other outbound connections.

After applying restrictions, run the offline build validation procedure again to confirm no implicit internet dependency was missed.

---

## Documentation Container in Air-Gap Mode

No additional steps are required — the documentation container is already offline-capable by default.

The MkDocs build uses the `privacy` plugin to download all external assets (fonts, JavaScript) at Docker build time and embed them in the image. At runtime, the nginx container serves only local files with no outbound requests.

**Verify:**

```bash
# Confirm the docs container starts without network access
docker run --network=none <DOCS_IMAGE> nginx -t
```

The container should start successfully even with `--network=none`.

---

## What Still Requires Internet

The following components cannot be fully air-gapped without substitution. This list is exhaustive — if a component is not listed here, it works offline.

| Component | Internet dependency | Suggested substitution |
|-----------|--------------------|-----------------------|
| Cloudflare Tunnel | Outbound to `*.cloudflare.com` for dashboard public access | On-premises reverse proxy: Traefik, nginx, or HAProxy with your own TLS certificate |
| Base image pulls (initial) | Docker Hub for `python:3.12-alpine`, `debian:12-slim`, `nginx:alpine`, and similar | Pre-pull all base images before isolation (`docker pull` + `docker tag` + push to local registry); update `compose.server.yaml` image references to point to the local registry |
| PowerShell installation (DEBIAN blueprint) | Downloads `.deb` from `github.com/PowerShell/PowerShell/releases` during Foundry build | Mirror the specific PowerShell `.deb` release to a local artifact store and update the DEBIAN capability matrix injection recipe to reference the local URL |
| Any `pip install` without mirror config | If `pypi_mirror_url` is not configured, pip defaults to `pypi.org` | Configure mirror URL before any builds — see Package Mirror Setup above |

!!! warning
    This table reflects the current implementation. If you add custom blueprints or Foundry templates that install packages from external sources, those dependencies are not automatically mirrored — review each new template before deploying in air-gap mode.

---

## Air-Gap Readiness Checklist

Use this checklist before completing the air-gap transition. Print or copy it to a separate document for offline reference.

```markdown
## Air-Gap Readiness Checklist

### Infrastructure
- [ ] Mirror sidecars (PyPI + APT) are deployed and running
- [ ] Mirror URLs configured via /admin/mirror-config (logged as mirror:config_updated)
- [ ] All required base images pre-pulled and pushed to local registry
- [ ] Cloudflare Tunnel replaced with on-prem reverse proxy (if public dashboard access is required)
- [ ] TLS certificate provisioned for on-prem reverse proxy

### Package mirrors
- [ ] All PyPI packages required by current Foundry templates are present in the PyPI mirror
- [ ] All APT packages required by current Foundry templates are present in the APT mirror
- [ ] PowerShell .deb mirrored to local artifact store (if DEBIAN blueprint is in use)
- [ ] Mirror seed verified — no packages are fetched from internet during seeding

### Validation
- [ ] Foundry build completed successfully with internet blocked (--no-cache, all layers rebuilt)
- [ ] Documentation site loads without external requests (browser Dev Tools → Network tab checked)
- [ ] Node enrollment completed successfully in isolated network environment
- [ ] A complete job run (enroll → assign → execute → result) confirmed end-to-end

### Ongoing operations
- [ ] Process defined for uploading new packages to mirrors after isolation
- [ ] Audit log export scheduled to external immutable store (S3 with object lock, SIEM, etc.)
- [ ] Base image update procedure documented for future security patches (pre-pull, tag, push to local registry)
- [ ] Incident response plan updated to reflect air-gap constraints
```
