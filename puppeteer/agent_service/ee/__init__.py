"""
EE plugin loader. Discovers axiom.ee entry_points and loads them.
If no EE plugin is installed, all feature flags are False and
stub routers serve 402 responses.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import logging

logger = logging.getLogger(__name__)

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


def _mount_ce_stubs(app: Any) -> None:
    from .interfaces.foundry import foundry_stub_router
    from .interfaces.audit import audit_stub_router
    from .interfaces.webhooks import webhooks_stub_router
    from .interfaces.triggers import triggers_stub_router
    from .interfaces.auth_ext import auth_ext_stub_router
    from .interfaces.smelter import smelter_stub_router
    app.include_router(foundry_stub_router)
    app.include_router(audit_stub_router)
    app.include_router(webhooks_stub_router)
    app.include_router(triggers_stub_router)
    app.include_router(auth_ext_stub_router)
    app.include_router(smelter_stub_router)
    logger.info("CE mode: mounted 6 stub routers (402 for all EE routes)")


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
