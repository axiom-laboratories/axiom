from fastapi import APIRouter
from fastapi.responses import JSONResponse

bundles_stub_router = APIRouter(tags=["Bundles"])

_EE_RESPONSE = JSONResponse(
    status_code=402,
    content={"detail": "This feature requires Axiom Enterprise Edition. See https://axiom.run/enterprise"}
)


@bundles_stub_router.get("/api/admin/bundles")
async def list_bundles(): return _EE_RESPONSE

@bundles_stub_router.post("/api/admin/bundles")
async def create_bundle(): return _EE_RESPONSE

@bundles_stub_router.get("/api/admin/bundles/{id}")
async def get_bundle(id: str): return _EE_RESPONSE

@bundles_stub_router.patch("/api/admin/bundles/{id}")
async def update_bundle(id: str): return _EE_RESPONSE

@bundles_stub_router.delete("/api/admin/bundles/{id}")
async def delete_bundle(id: str): return _EE_RESPONSE

@bundles_stub_router.post("/api/admin/bundles/{id}/items")
async def add_bundle_item(id: str): return _EE_RESPONSE

@bundles_stub_router.patch("/api/admin/bundles/{id}/items/{item_id}")
async def update_bundle_item(id: str, item_id: int): return _EE_RESPONSE

@bundles_stub_router.delete("/api/admin/bundles/{id}/items/{item_id}")
async def delete_bundle_item(id: str, item_id: int): return _EE_RESPONSE

@bundles_stub_router.post("/api/foundry/apply-bundle/{bundle_id}")
async def apply_bundle(bundle_id: str): return _EE_RESPONSE
