# Phase 13 Research: Package & Repository Mirroring

## Standard Stack
- **Python (PyPI)**: `pypiserver/pypiserver`
    - **Rationale**: Minimal, fast, and PEP 503 compliant. Supports serving packages from a local directory.
    - **Configuration**: Run with `-P . -a .` for no-auth (internal only) or `-P .htpasswd` for basic auth.
- **System (APT)**: `reprepro` + `Nginx`
    - **Rationale**: `reprepro` is the industry standard for creating and managing small to medium-sized Debian repositories. Nginx will serve the resulting static file structure.
    - **Signing**: Uses GPG for `Release` file signing.
- **Storage**: Shared Docker Volume `mirror-data`
    - Mounted at `/data/pypi` for `pypiserver`.
    - Mounted at `/var/www/apt` for `nginx`.

## Architecture Patterns
- **Foundry Injection**:
    - **PIP**: Inject `/etc/pip.conf` into the build context:
      ```ini
      [global]
      index-url = http://pypi:8080/simple
      trusted-host = pypi
      ```
    - **APT**: Inject a custom `sources.list` pointing to `http://apt-mirror/` and add the Smelter GPG key to `/etc/apt/trusted.gpg.d/smelter.gpg`.
- **Automatic Ingestion**:
    - `SmelterService` will use `pip download --dest /data/pypi` to fetch new ingredients.
    - `SmelterService` will use `reprepro -b /var/www/apt includedeb` to add `.deb` files.

## Don't Hand-Roll
- **PEP 503 API**: Use `pypiserver`. Building a custom simple-index server is error-prone and unnecessary.
- **APT Repository Structure**: Use `reprepro`. Manually managing `Release` and `Packages` files leads to broken metadata and GPG errors.

## Common Pitfalls
- **GPG Key Management**: If the Smelter GPG key is not imported correctly during the build's early stages, `apt-get` will fail with "The following signatures were invalid".
- **Trusted Hosts**: Since internal mirrors often run over HTTP, `pip` must be explicitly told to trust the mirror host via `--trusted-host` or `pip.conf`.
- **Architectural Mismatch**: Ensure `reprepro` is configured for the correct architectures (amd64, arm64) used by the Puppets.

## Code Examples

### 1. Nginx Config for APT Repo
```nginx
server {
    listen 80;
    root /var/www/apt;
    autoindex on;
    location / {
        try_files $uri $uri/ =404;
    }
}
```

### 2. Reprepro Distribution Config
```text
Origin: Smelter
Label: Smelter-Local
Codename: stable
Architectures: amd64 arm64
Components: main
Description: Vetted Puppet Ingredients
SignWith: <GPG_KEY_ID>
```

## RESEARCH COMPLETE
Confidence Level: High (Standard tools and patterns identified).
Next Step: /gsd:plan-phase 13
