import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from agent_service.main import enroll_node
from agent_service.services.job_service import JobService
from agent_service.db import PuppetTemplate, Node, Token

@pytest.mark.asyncio
async def test_enrollment_blocked_for_revoked_image():
    """Verify enrollment fails if the target template is REVOKED."""
    mock_db = AsyncMock()
    token_entry = Token(token="t1", used=False, template_id="tmpl1")
    tmpl = PuppetTemplate(id="tmpl1", status="REVOKED")
    
    async def mock_execute(stmt):
        m = MagicMock()
        if "tokens" in str(stmt).lower(): m.scalar_one_or_none.return_value = token_entry
        elif "puppet_templates" in str(stmt).lower(): m.scalar_one_or_none.return_value = tmpl
        return m
    
    mock_db.execute.side_effect = mock_execute
    
    from puppeteer.agent_service.models import EnrollmentRequest
    req = EnrollmentRequest(token="t1", hostname="test", csr_pem="...", node_secret_hash="...", machine_id="...")
    
    with patch("puppeteer.agent_service.main.pki_service") as mock_pki:
        mock_pki.sign_csr.return_value = "signed-cert"
        with pytest.raises(HTTPException) as excinfo:
            await enroll_node(req, MagicMock(), mock_db)
        assert excinfo.value.status_code == 403
        assert "REVOKED" in excinfo.value.detail

@pytest.mark.asyncio
async def test_pull_work_blocked_for_revoked_image():
    """Verify nodes on REVOKED images get 0 concurrency (blocking)."""
    mock_db = AsyncMock()
    node = Node(node_id="n1", template_id="tmpl1", job_memory_limit="512m")
    tmpl = PuppetTemplate(id="tmpl1", status="REVOKED", friendly_name="Malicious")
    
    async def mock_execute(stmt):
        m = MagicMock()
        if "nodes" in str(stmt).lower(): m.scalar_one_or_none.return_value = node
        elif "puppet_templates" in str(stmt).lower(): m.scalar_one_or_none.return_value = tmpl
        return m
    
    mock_db.execute.side_effect = mock_execute
    
    resp = await JobService.pull_work("n1", "1.2.3.4", mock_db)
    assert resp.job is None
    assert resp.config.concurrency_limit == 0
