from fastapi import APIRouter
from fastapi.responses import JSONResponse

execution_stub_router = APIRouter(tags=["Execution Records"])

_EE_RESPONSE = JSONResponse(
    status_code=402,
    content={"detail": "This feature requires Axiom Enterprise Edition. See https://axiom.run/enterprise"}
)


@execution_stub_router.get("/api/executions")
async def list_executions_stub(): return _EE_RESPONSE

@execution_stub_router.get("/api/executions/{id}")
async def get_execution_stub(id: int): return _EE_RESPONSE

@execution_stub_router.get("/api/executions/{id}/attestation")
async def get_execution_attestation_stub(id: int): return _EE_RESPONSE

@execution_stub_router.get("/jobs/{guid}/executions")
async def list_job_executions_stub(guid: str): return _EE_RESPONSE

@execution_stub_router.patch("/api/executions/{exec_id}/pin")
async def pin_execution_stub(exec_id: int): return _EE_RESPONSE

@execution_stub_router.patch("/api/executions/{exec_id}/unpin")
async def unpin_execution_stub(exec_id: int): return _EE_RESPONSE

@execution_stub_router.get("/api/jobs/{guid}/executions/export")
async def export_job_executions_stub(guid: str): return _EE_RESPONSE
