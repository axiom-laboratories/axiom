from fastapi import APIRouter
from fastapi.responses import JSONResponse

foundry_stub_router = APIRouter(tags=["Foundry"])

_EE_RESPONSE = JSONResponse(
    status_code=402,
    content={"detail": "This feature requires Axiom Enterprise Edition. See https://axiom.run/enterprise"}
)


@foundry_stub_router.get("/api/blueprints")
async def blueprints_get(): return _EE_RESPONSE

@foundry_stub_router.post("/api/blueprints")
async def blueprints_post(): return _EE_RESPONSE

@foundry_stub_router.get("/api/blueprints/{blueprint_id}")
async def blueprint_get(blueprint_id: str): return _EE_RESPONSE

@foundry_stub_router.put("/api/blueprints/{blueprint_id}")
async def blueprint_put(blueprint_id: str): return _EE_RESPONSE

@foundry_stub_router.delete("/api/blueprints/{blueprint_id}")
async def blueprint_delete(blueprint_id: str): return _EE_RESPONSE

@foundry_stub_router.get("/api/templates")
async def templates_get(): return _EE_RESPONSE

@foundry_stub_router.post("/api/templates")
async def templates_post(): return _EE_RESPONSE

@foundry_stub_router.get("/api/templates/{template_id}")
async def template_get(template_id: str): return _EE_RESPONSE

@foundry_stub_router.put("/api/templates/{template_id}")
async def template_put(template_id: str): return _EE_RESPONSE

@foundry_stub_router.delete("/api/templates/{template_id}")
async def template_delete(template_id: str): return _EE_RESPONSE

@foundry_stub_router.patch("/api/templates/{template_id}/status")
async def templates_status_patch(template_id: str): return _EE_RESPONSE

@foundry_stub_router.post("/api/templates/{template_id}/build")
async def template_build(template_id: str): return _EE_RESPONSE

@foundry_stub_router.get("/api/templates/{template_id}/bom")
async def template_bom(template_id: str): return _EE_RESPONSE

@foundry_stub_router.get("/api/capability-matrix")
async def capability_matrix_get(): return _EE_RESPONSE

@foundry_stub_router.post("/api/capability-matrix")
async def capability_matrix_post(): return _EE_RESPONSE

@foundry_stub_router.put("/api/capability-matrix/{entry_id}")
async def capability_matrix_put(entry_id: str): return _EE_RESPONSE

@foundry_stub_router.delete("/api/capability-matrix/{entry_id}")
async def capability_matrix_delete(entry_id: str): return _EE_RESPONSE

@foundry_stub_router.get("/api/images")
async def images_get(): return _EE_RESPONSE

@foundry_stub_router.post("/foundry/build")
async def foundry_build(): return _EE_RESPONSE

@foundry_stub_router.get("/foundry/definitions")
async def foundry_definitions_get(): return _EE_RESPONSE

@foundry_stub_router.post("/admin/mark-base-updated")
async def mark_base_updated(): return _EE_RESPONSE

@foundry_stub_router.get("/admin/base-image-updated")
async def base_image_updated(): return _EE_RESPONSE

@foundry_stub_router.get("/api/foundry/search-packages")
async def foundry_search_packages(): return _EE_RESPONSE
