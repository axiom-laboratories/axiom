from fastapi import APIRouter
from fastapi.responses import JSONResponse

analyzer_stub_router = APIRouter(tags=["Script Analyzer"])

_EE_RESPONSE = JSONResponse(
    status_code=402,
    content={"detail": "This feature requires Axiom Enterprise Edition. See https://axiom.run/enterprise"}
)


@analyzer_stub_router.post("/api/analyzer/analyze-script")
async def analyzer_analyze_script(): return _EE_RESPONSE

@analyzer_stub_router.get("/api/analyzer/requests")
async def analyzer_requests_get(): return _EE_RESPONSE

@analyzer_stub_router.post("/api/analyzer/requests")
async def analyzer_requests_post(): return _EE_RESPONSE

@analyzer_stub_router.post("/api/analyzer/requests/{request_id}/approve")
async def analyzer_request_approve(request_id: str): return _EE_RESPONSE

@analyzer_stub_router.post("/api/analyzer/requests/{request_id}/reject")
async def analyzer_request_reject(request_id: str): return _EE_RESPONSE
