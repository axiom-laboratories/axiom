"""
EE plugin loader. Discovers axiom.ee entry_points and loads them.
If no EE plugin is installed, all feature flags are False and
stub routers serve 402 responses.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import logging
import subprocess
import sys
import glob
import os
import json
import base64
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

logger = logging.getLogger(__name__)

# Tag applied to stub routes so they can be identified and removed
_STUB_TAG = "__ee_stub__"

# ---------------------------------------------------------------------------
# EE Wheel Manifest Verification
# Manifest path and verification public key — read from env var for key rotation
# (Phase 164 QUAL-02: moved from hardcoded source to env var)
# ---------------------------------------------------------------------------
MANIFEST_PATH = Path("/tmp/axiom_ee.manifest.json")

def _load_manifest_public_key() -> bytes:
    """Load MANIFEST_PUBLIC_KEY from environment variable.

    Raises:
        RuntimeError: if MANIFEST_PUBLIC_KEY environment variable is not set.
    """
    key_pem = os.getenv("MANIFEST_PUBLIC_KEY", "")
    if not key_pem:
        raise RuntimeError(
            "MANIFEST_PUBLIC_KEY environment variable not set. "
            "Required for EE manifest verification (Phase 164 QUAL-02)."
        )
    return key_pem.encode() if isinstance(key_pem, str) else key_pem

MANIFEST_PUBLIC_KEY = _load_manifest_public_key()
_manifest_pub_key: Ed25519PublicKey = serialization.load_pem_public_key(MANIFEST_PUBLIC_KEY)  # type: ignore[assignment]

@dataclass
class EEContext:
    """Holds feature flags and references to EE router instances."""
    foundry: bool = False
    audit: bool = False
    webhooks: bool = False
    triggers: bool = False
    rbac: bool = False
    resource_limits: bool = False
    service_principals: bool = False
    api_keys: bool = False
    executions: bool = False


def _mount_ce_stubs(app: Any) -> None:
    from .interfaces.foundry import foundry_stub_router
    from .interfaces.audit import audit_stub_router
    from .interfaces.webhooks import webhooks_stub_router
    from .interfaces.triggers import triggers_stub_router
    from .interfaces.auth_ext import auth_ext_stub_router
    from .interfaces.smelter import smelter_stub_router
    from .interfaces.executions import execution_stub_router
    from .interfaces.analyzer import analyzer_stub_router
    from .interfaces.bundles import bundles_stub_router

    # Snapshot route count before mounting stubs
    pre_count = len(app.routes)

    app.include_router(foundry_stub_router)
    app.include_router(audit_stub_router)
    app.include_router(webhooks_stub_router)
    app.include_router(triggers_stub_router)
    app.include_router(auth_ext_stub_router)
    app.include_router(smelter_stub_router)
    app.include_router(execution_stub_router)
    app.include_router(analyzer_stub_router)
    app.include_router(bundles_stub_router)

    # Tag every route added by stub routers
    for route in app.routes[pre_count:]:
        route.tags = list(getattr(route, "tags", []) or []) + [_STUB_TAG]

    logger.info("CE mode: mounted %d stub routes (402 for all EE routes)", len(app.routes) - pre_count)


def _remove_ce_stubs(app: Any) -> int:
    """Remove all stub-tagged routes. Returns count removed."""
    original = len(app.routes)
    app.routes[:] = [
        r for r in app.routes
        if _STUB_TAG not in (getattr(r, "tags", None) or [])
    ]
    removed = original - len(app.routes)
    if removed:
        logger.info("Removed %d CE stub routes", removed)
    return removed


def _verify_wheel_manifest(wheel_path: str) -> None:
    """Verify the EE wheel manifest signature and SHA256 hash.

    Performs 6-step verification:
    1. Check manifest file exists
    2. Parse JSON and validate required fields (sha256, signature)
    3. Compute SHA256 of wheel bytes
    4. Assert computed SHA256 matches manifest
    5. Decode signature from base64
    6. Verify Ed25519 signature over hex SHA256 string (UTF-8 encoded)

    Raises RuntimeError on any verification failure.
    """
    # Step 1: Check manifest file exists
    if not MANIFEST_PATH.exists():
        raise RuntimeError(
            f"Manifest not found: {MANIFEST_PATH} (wheel: {wheel_path})"
        )

    # Step 2: Parse JSON and validate required fields
    try:
        with open(MANIFEST_PATH, 'r') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Manifest JSON malformed at {MANIFEST_PATH}: {e}"
        )

    if 'sha256' not in manifest:
        raise RuntimeError(
            f"Manifest missing required field 'sha256' at {MANIFEST_PATH}"
        )
    if 'signature' not in manifest:
        raise RuntimeError(
            f"Manifest missing required field 'signature' at {MANIFEST_PATH}"
        )

    manifest_sha256 = manifest['sha256']
    signature_b64 = manifest['signature']

    # Step 3: Compute SHA256 of wheel bytes
    try:
        sha256_hash = hashlib.sha256()
        with open(wheel_path, 'rb') as f:
            while chunk := f.read(65536):  # 64KB chunks
                sha256_hash.update(chunk)
        computed_sha256 = sha256_hash.hexdigest()
    except (OSError, IOError) as e:
        raise RuntimeError(
            f"Failed to read wheel file {wheel_path}: {e}"
        )

    # Step 4: Assert computed SHA256 matches manifest
    if computed_sha256 != manifest_sha256:
        raise RuntimeError(
            f"Wheel SHA256 mismatch: computed={computed_sha256}, "
            f"manifest={manifest_sha256} (wheel: {wheel_path})"
        )

    # Step 5: Decode signature from base64
    try:
        signature_bytes = base64.b64decode(signature_b64)
    except Exception as e:
        raise RuntimeError(
            f"Failed to decode signature as base64: {e}"
        )

    # Step 6: Verify Ed25519 signature over hex SHA256 string (UTF-8 encoded)
    signature_message = computed_sha256.encode('utf-8')
    try:
        _manifest_pub_key.verify(signature_bytes, signature_message)
    except Exception as e:
        raise RuntimeError(
            f"Wheel signature verification failed: {e} (wheel: {wheel_path})"
        )

    logger.info("Manifest verification passed for wheel: %s", wheel_path)


def _install_ee_wheel() -> bool:
    """Install the EE wheel from /tmp/ and apply source patches.

    Raises RuntimeError if manifest verification fails.
    Returns True if installation succeeded, False otherwise.
    """
    wheels = glob.glob("/tmp/axiom_ee-*.whl")
    if not wheels:
        logger.warning("No EE wheel found in /tmp/")
        return False

    wheel_path = wheels[0]
    logger.info("Installing EE wheel: %s", wheel_path)

    # Verify manifest signature and wheel hash before pip install
    _verify_wheel_manifest(wheel_path)

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--no-deps", "--no-cache-dir", wheel_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        logger.error("EE wheel install failed: %s", e)
        return False

    # Apply ee_patches (same logic as Containerfile)
    patches_dir = "/tmp/ee_patches/ee"
    if os.path.isdir(patches_dir):
        try:
            import ee as _ee_mod
            ee_site = os.path.dirname(_ee_mod.__file__)
            patched = 0
            for root, _dirs, files in os.walk(patches_dir):
                for fname in files:
                    if not fname.endswith(".py") or fname == "__init__.py":
                        continue
                    src = os.path.join(root, fname)
                    rel = os.path.relpath(src, patches_dir)
                    target = os.path.join(ee_site, rel)
                    # Remove compiled .so if present (patches override Cython builds)
                    so_target = target.replace(".py", f".cpython-{sys.version_info.major}{sys.version_info.minor}-x86_64-linux-musl.so")
                    if os.path.exists(so_target):
                        os.remove(so_target)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(src, "rb") as sf:
                        data = sf.read()
                    with open(target, "wb") as tf:
                        tf.write(data)
                    patched += 1
            logger.info("Applied %d EE source patches", patched)
        except Exception as e:
            logger.warning("EE patch application failed: %s", e)

    # Invalidate importlib caches so entry_points() picks up the new package
    import importlib
    importlib.invalidate_caches()

    return True


async def activate_ee_live(app: Any, engine: Any) -> EEContext | None:
    """Install EE wheel, remove stubs, and load real EE plugins.

    Stores error message in app.state.ee_activation_error if activation fails.

    Called from the licence reload endpoint when licence is valid but
    EE plugin is not yet loaded. Returns the new EEContext on success,
    or None if activation failed.
    """
    # Check if already active
    existing = getattr(app.state, "ee", None)
    if existing and existing.foundry:
        logger.info("EE already active, skipping activation")
        return existing

    # Install wheel with manifest verification
    try:
        if not _install_ee_wheel():
            return None
    except RuntimeError as e:
        error_msg = str(e)
        app.state.ee_activation_error = error_msg
        logger.error("EE activation failed: %s", error_msg)
        return None

    # Clear error on successful install
    app.state.ee_activation_error = None

    # Verify entry points are now discoverable
    from importlib.metadata import entry_points
    plugins = list(entry_points(group="axiom.ee"))
    if not plugins:
        logger.error("EE wheel installed but no axiom.ee entry points found")
        return None

    # Remove stub routes before mounting real ones
    _remove_ce_stubs(app)

    # Load real EE plugins
    ctx = EEContext()
    try:
        for ep in plugins:
            # EE-04: Entry point whitelist validation — same check as load_ee_plugins()
            if ep.value != "ee.plugin:EEPlugin":
                raise RuntimeError(
                    f"Untrusted axiom.ee entry point: '{ep.value}' — expected 'ee.plugin:EEPlugin'"
                )

            plugin_cls = ep.load()
            plugin = plugin_cls(app, engine)
            await plugin.register(ctx)
            logger.info("Live-activated EE plugin: %s", ep.name)
    except Exception as e:
        logger.error("EE plugin registration failed: %s — remounting stubs", e)
        _mount_ce_stubs(app)
        return None

    return ctx


async def load_ee_plugins(app: Any, engine: Any) -> EEContext:
    """
    Discover and load EE plugins via importlib.metadata entry_points.
    Entry point group: 'axiom.ee'

    If no EE plugin found, registers stub routers that return 402.
    """
    ctx = EEContext()

    try:
        from importlib.metadata import entry_points
        plugins = list(entry_points(group="axiom.ee"))
        if plugins:
            for ep in plugins:
                # EE-04: Entry point whitelist validation — exact value match only
                if ep.value != "ee.plugin:EEPlugin":
                    raise RuntimeError(
                        f"Untrusted axiom.ee entry point: '{ep.value}' — expected 'ee.plugin:EEPlugin'"
                    )

                plugin_cls = ep.load()
                plugin = plugin_cls(app, engine)
                await plugin.register(ctx)
                logger.info(f"Loaded EE plugin: {ep.name}")
        else:
            logger.info("No EE plugins found — running in CE mode")
            _mount_ce_stubs(app)
    except Exception as e:
        logger.warning(f"EE plugin load failed ({e}), continuing in CE mode")
        _mount_ce_stubs(app)

    return ctx
