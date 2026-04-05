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

logger = logging.getLogger(__name__)

# Tag applied to stub routes so they can be identified and removed
_STUB_TAG = "__ee_stub__"

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


def _install_ee_wheel() -> bool:
    """Install the EE wheel from /tmp/ and apply source patches.

    Returns True if installation succeeded, False otherwise.
    """
    wheels = glob.glob("/tmp/axiom_ee-*.whl")
    if not wheels:
        logger.warning("No EE wheel found in /tmp/")
        return False

    wheel_path = wheels[0]
    logger.info("Installing EE wheel: %s", wheel_path)

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

    Called from the licence reload endpoint when licence is valid but
    EE plugin is not yet loaded. Returns the new EEContext on success,
    or None if activation failed.
    """
    # Check if already active
    existing = getattr(app.state, "ee", None)
    if existing and existing.foundry:
        logger.info("EE already active, skipping activation")
        return existing

    # Install the wheel
    if not _install_ee_wheel():
        return None

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
