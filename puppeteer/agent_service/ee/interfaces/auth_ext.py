from fastapi import APIRouter
from fastapi.responses import JSONResponse

auth_ext_stub_router = APIRouter(tags=["Auth Extensions"])

_EE_RESPONSE = JSONResponse(
    status_code=402,
    content={"detail": "This feature requires Axiom Enterprise Edition. See https://axiom.run/enterprise"}
)


@auth_ext_stub_router.get("/admin/service-principals")
async def service_principals_get(): return _EE_RESPONSE

@auth_ext_stub_router.post("/admin/service-principals")
async def service_principals_post(): return _EE_RESPONSE

@auth_ext_stub_router.get("/admin/service-principals/{sp_id}")
async def service_principal_get(sp_id: str): return _EE_RESPONSE

@auth_ext_stub_router.patch("/admin/service-principals/{sp_id}")
async def service_principal_patch(sp_id: str): return _EE_RESPONSE

@auth_ext_stub_router.delete("/admin/service-principals/{sp_id}")
async def service_principal_delete(sp_id: str): return _EE_RESPONSE

@auth_ext_stub_router.post("/admin/service-principals/{sp_id}/rotate-secret")
async def service_principal_rotate_secret(sp_id: str): return _EE_RESPONSE

@auth_ext_stub_router.get("/auth/me/signing-keys")
async def signing_keys_get(): return _EE_RESPONSE

@auth_ext_stub_router.post("/auth/me/signing-keys")
async def signing_keys_post(): return _EE_RESPONSE

@auth_ext_stub_router.get("/auth/me/signing-keys/{key_id}")
async def signing_key_get(key_id: str): return _EE_RESPONSE

@auth_ext_stub_router.delete("/auth/me/signing-keys/{key_id}")
async def signing_key_delete(key_id: str): return _EE_RESPONSE

@auth_ext_stub_router.get("/auth/me/api-keys")
async def api_keys_get(): return _EE_RESPONSE

@auth_ext_stub_router.post("/auth/me/api-keys")
async def api_keys_post(): return _EE_RESPONSE

@auth_ext_stub_router.get("/auth/me/api-keys/{key_id}")
async def api_key_get(key_id: str): return _EE_RESPONSE

@auth_ext_stub_router.delete("/auth/me/api-keys/{key_id}")
async def api_key_delete(key_id: str): return _EE_RESPONSE

@auth_ext_stub_router.get("/admin/users")
async def users_get(): return _EE_RESPONSE

@auth_ext_stub_router.post("/admin/users")
async def users_post(): return _EE_RESPONSE

@auth_ext_stub_router.get("/admin/users/{username}")
async def user_get(username: str): return _EE_RESPONSE

@auth_ext_stub_router.put("/admin/users/{username}")
async def user_put(username: str): return _EE_RESPONSE

@auth_ext_stub_router.delete("/admin/users/{username}")
async def user_delete(username: str): return _EE_RESPONSE

@auth_ext_stub_router.patch("/admin/users/{username}")
async def user_patch(username: str): return _EE_RESPONSE

@auth_ext_stub_router.get("/admin/roles/{role}/permissions")
async def role_permissions_get(role: str): return _EE_RESPONSE

@auth_ext_stub_router.post("/admin/roles/{role}/permissions")
async def role_permissions_post(role: str): return _EE_RESPONSE

@auth_ext_stub_router.delete("/admin/roles/{role}/permissions/{permission}")
async def role_permission_delete(role: str, permission: str): return _EE_RESPONSE
