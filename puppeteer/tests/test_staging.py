import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from agent_service.services.staging_service import StagingService
from agent_service.db import PuppetTemplate

@pytest.mark.asyncio
async def test_run_smelt_check_success():
    """Verify Smelt-Check correctly reports success."""
    tmpl = PuppetTemplate(id="t1", friendly_name="test", current_image_uri="localhost:5000/test:latest")
    
    with patch("puppeteer.agent_service.services.staging_service.AsyncSessionLocal") as mock_session_factory:
        mock_db = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = tmpl
        mock_db.execute.return_value = mock_res

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"All checks passed", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            report = await StagingService.run_smelt_check("t1", "test-cmd")
            assert report["status"] == "SUCCESS"
            assert "All checks passed" in report["logs"]

@pytest.mark.asyncio
async def test_capture_bom_logic():
    """Verify BOM capture populates DB models."""
    tmpl = PuppetTemplate(id="t1", friendly_name="test", current_image_uri="localhost:5000/test:latest")
    pip_json = json.dumps([{"name": "requests", "version": "2.20.0"}]).encode()
    apt_str = b"curl==7.81.0\ngit==2.34.1\n"

    with patch("puppeteer.agent_service.services.staging_service.AsyncSessionLocal") as mock_session_factory:
        mock_db = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = tmpl
        mock_db.execute.return_value = mock_res

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # First call for PIP, second for APT
            mock_proc_pip = AsyncMock()
            mock_proc_pip.communicate.return_value = (pip_json, b"")
            mock_proc_pip.returncode = 0

            mock_proc_apt = AsyncMock()
            mock_proc_apt.communicate.return_value = (apt_str, b"")
            mock_proc_apt.returncode = 0

            mock_exec.side_effect = [mock_proc_pip, mock_proc_apt]

            bom = await StagingService.capture_bom("t1")
            assert bom is not None
            assert len(bom["pip"]) == 1
            assert len(bom["apt"]) == 2
            
            # Verify DB additions (Raw BOM + 3 Index entries)
            # count calls to mock_db.add
            assert mock_db.add.call_count == 4
            assert tmpl.bom_captured is True
            mock_db.commit.assert_called()
