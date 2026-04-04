"""
Tests for script analysis service (Phase 113).
TDD approach: RED phase defines expected behavior.
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

# Unit tests — no DB dependency


class TestPythonAstExtraction:
    """Python script AST-based import extraction."""

    def test_simple_import_extraction(self):
        """Extract 'requests' from simple import statement."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "import requests"
        result = AnalyzerService._analyze_python(script)

        assert len(result) == 1
        assert result[0]["import_name"] == "requests"
        assert result[0]["package_name"] == "requests"

    def test_import_cv2_maps_to_opencv(self):
        """Extract 'cv2' and map to 'opencv-python'."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "import cv2"
        result = AnalyzerService._analyze_python(script)

        assert len(result) == 1
        assert result[0]["import_name"] == "cv2"
        assert result[0]["package_name"] == "opencv-python"
        assert result[0]["mapped"] is True

    def test_multiple_imports(self):
        """Extract multiple imports from one script."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "import requests\nimport cv2\nimport numpy"
        result = AnalyzerService._analyze_python(script)

        assert len(result) == 3
        package_names = {r["package_name"] for r in result}
        assert "requests" in package_names
        assert "opencv-python" in package_names
        assert "numpy" in package_names

    def test_from_import_statement(self):
        """Extract module from 'from X import Y' statement."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "from bs4 import BeautifulSoup"
        result = AnalyzerService._analyze_python(script)

        assert len(result) == 1
        assert result[0]["import_name"] == "bs4"
        assert result[0]["package_name"] == "beautifulsoup4"


class TestPythonStdlibExclusion:
    """Python standard library modules are excluded."""

    def test_stdlib_modules_excluded(self):
        """Exclude sys, os, json, etc. from results."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "import sys\nimport os\nimport json\nimport requests"
        result = AnalyzerService._analyze_python(script)

        # Only requests should be in results
        assert len(result) == 1
        assert result[0]["package_name"] == "requests"

    def test_future_imports_excluded(self):
        """Exclude __future__ imports (stdlib)."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "from __future__ import annotations\nimport requests"
        result = AnalyzerService._analyze_python(script)

        assert len(result) == 1
        assert result[0]["package_name"] == "requests"


class TestPythonImportMappings:
    """Import-to-package mappings for non-obvious packages."""

    def test_pil_maps_to_pillow(self):
        """PIL import maps to Pillow package."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "from PIL import Image"
        result = AnalyzerService._analyze_python(script)

        assert len(result) == 1
        assert result[0]["import_name"] == "PIL"
        assert result[0]["package_name"] == "Pillow"

    def test_sklearn_maps_to_scikit_learn(self):
        """sklearn import maps to scikit-learn package."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "from sklearn import datasets"
        result = AnalyzerService._analyze_python(script)

        assert len(result) == 1
        assert result[0]["package_name"] == "scikit-learn"


class TestMalformedPythonScript:
    """Handle malformed/broken Python scripts gracefully."""

    def test_syntax_error_returns_empty_list(self):
        """SyntaxError in script returns empty list, no crash."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "from import foo"  # Invalid syntax
        result = AnalyzerService._analyze_python(script)

        # Should not raise, should return empty list
        assert result == []

    def test_empty_script_returns_empty_list(self):
        """Empty script returns empty list."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = ""
        result = AnalyzerService._analyze_python(script)

        assert result == []


class TestLanguageDetection:
    """Language auto-detection from shebang and syntax patterns."""

    def test_python_shebang_detection(self):
        """Detect Python from #!/usr/bin/env python shebang."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "#!/usr/bin/env python\nimport requests"
        lang = AnalyzerService._detect_language(script)

        assert lang == "python"

    def test_bash_shebang_detection(self):
        """Detect Bash from #!/bin/bash shebang."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "#!/bin/bash\napt-get install curl"
        lang = AnalyzerService._detect_language(script)

        assert lang == "bash"

    def test_powershell_shebang_detection(self):
        """Detect PowerShell from #!powershell shebang."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "#!powershell\nImport-Module PSReadLine"
        lang = AnalyzerService._detect_language(script)

        assert lang == "powershell"

    def test_python_syntax_detection(self):
        """Detect Python from 'import' keyword without shebang."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "import requests"
        lang = AnalyzerService._detect_language(script)

        assert lang == "python"

    def test_bash_apt_get_syntax_detection(self):
        """Detect Bash from 'apt-get install' without shebang."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "apt-get install curl"
        lang = AnalyzerService._detect_language(script)

        assert lang == "bash"


class TestBashPackageExtraction:
    """Bash script package extraction via regex."""

    def test_apt_get_install_extraction(self):
        """Extract packages from 'apt-get install' command."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "apt-get install curl wget"
        result = AnalyzerService._analyze_bash(script)

        package_names = {r["package_name"] for r in result}
        assert "curl" in package_names
        assert "wget" in package_names

    def test_yum_install_extraction(self):
        """Extract packages from 'yum install' command."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "yum install httpd"
        result = AnalyzerService._analyze_bash(script)

        assert len(result) == 1
        assert result[0]["package_name"] == "httpd"

    def test_apk_add_extraction(self):
        """Extract packages from 'apk add' command."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "apk add bash"
        result = AnalyzerService._analyze_bash(script)

        assert len(result) == 1
        assert result[0]["package_name"] == "bash"

    def test_version_specifier_stripping(self):
        """Strip version specifiers (==, >=, <=, etc.) from package names."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "apt-get install curl==7.68.0 wget>=1.20"
        result = AnalyzerService._analyze_bash(script)

        package_names = {r["package_name"] for r in result}
        assert "curl" in package_names
        assert "wget" in package_names
        assert "curl==7.68.0" not in package_names


class TestPowerShellModuleExtraction:
    """PowerShell script module extraction via regex."""

    def test_import_module_extraction(self):
        """Extract modules from 'Import-Module' command."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "Import-Module PSReadLine"
        result = AnalyzerService._analyze_powershell(script)

        assert len(result) == 1
        assert result[0]["package_name"] == "PSReadLine"

    def test_install_module_extraction(self):
        """Extract modules from 'Install-Module' command."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "Install-Module Az.Storage"
        result = AnalyzerService._analyze_powershell(script)

        assert len(result) == 1
        assert result[0]["package_name"] == "Az.Storage"

    def test_install_module_with_name_parameter(self):
        """Extract modules from 'Install-Module -Name' syntax."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "Install-Module -Name AzureRM"
        result = AnalyzerService._analyze_powershell(script)

        assert len(result) == 1
        assert result[0]["package_name"] == "AzureRM"


class TestLanguageDispatch:
    """Analyzer dispatches to correct language handler."""

    @pytest.mark.asyncio
    async def test_analyze_script_dispatches_to_python(self):
        """analyze_script with Python content calls _analyze_python."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "import requests"
        result = await AnalyzerService.analyze_script(script, language="python")

        assert result["detected_language"] == "python"
        assert len(result["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_script_auto_detects_language(self):
        """analyze_script auto-detects language if not provided."""
        from agent_service.services.analyzer_service import AnalyzerService

        script = "#!/bin/bash\napt-get install curl"
        result = await AnalyzerService.analyze_script(script)

        assert result["detected_language"] == "bash"

    @pytest.mark.asyncio
    async def test_analyze_script_respects_language_override(self):
        """analyze_script respects explicit language parameter."""
        from agent_service.services.analyzer_service import AnalyzerService

        # Script looks like bash, but force python
        script = "apt-get install curl"
        result = await AnalyzerService.analyze_script(script, language="python")

        assert result["detected_language"] == "python"


class TestImportMappingCompleteness:
    """Import mapping dict covers common packages."""

    def test_mapping_dict_exists(self):
        """Static IMPORT_TO_PACKAGE dict defined."""
        from agent_service.services.analyzer_service import AnalyzerService

        assert hasattr(AnalyzerService, "IMPORT_TO_PACKAGE")
        assert isinstance(AnalyzerService.IMPORT_TO_PACKAGE, dict)

    def test_mapping_dict_has_common_entries(self):
        """Mapping dict includes cv2, PIL, yaml, sklearn, etc."""
        from agent_service.services.analyzer_service import AnalyzerService

        mapping = AnalyzerService.IMPORT_TO_PACKAGE

        # Common cases from RESEARCH.md
        assert "cv2" in mapping
        assert mapping["cv2"] == "opencv-python"

        assert "PIL" in mapping
        assert mapping["PIL"] == "Pillow"

        assert "yaml" in mapping
        assert mapping["yaml"] == "PyYAML"

        assert "sklearn" in mapping
        assert mapping["sklearn"] == "scikit-learn"

        assert "bs4" in mapping
        assert mapping["bs4"] == "beautifulsoup4"


class TestAnalyzerEndpointAuth:
    """Endpoint requires authentication."""

    @pytest.mark.asyncio
    async def test_analyze_script_endpoint_requires_auth(self):
        """POST /api/analyzer/analyze-script returns 401 without auth token."""
        # This test is integration-level and requires FastAPI test client
        # Placeholder for integration test phase
        pass


# Integration Tests — Endpoint layer (require FastAPI test client + DB)

class TestAnalyzerEndpointIntegration:
    """Integration tests for analyzer router endpoints."""

    @pytest.mark.asyncio
    async def test_analyze_script_endpoint_response_format(self):
        """Endpoint returns AnalyzeScriptResponse with suggestions and approval status."""
        from agent_service.services.analyzer_service import AnalyzerService
        from agent_service.models import AnalyzeScriptRequest

        script = "import requests\nimport numpy"
        req = AnalyzeScriptRequest(script_content=script, language="python")

        # Simulate endpoint call by calling service directly
        result = await AnalyzerService.analyze_script(req.script_content, req.language)

        # Verify response format
        assert "detected_language" in result
        assert "suggestions" in result
        assert result["detected_language"] == "python"
        assert len(result["suggestions"]) >= 2

        # Verify suggestion format
        for suggestion in result["suggestions"]:
            assert "import_name" in suggestion
            assert "package_name" in suggestion
            assert "ecosystem" in suggestion

    @pytest.mark.asyncio
    async def test_duplicate_request_prevention(self):
        """Creating a duplicate request should return 409 conflict."""
        # This test requires actual DB and current_user context
        # Marked as TODO for integration test phase with FastAPI test client
        pass

    @pytest.mark.asyncio
    async def test_approval_creates_ingredient(self):
        """Approving a request creates an ApprovedIngredient if not exists."""
        # This test requires actual DB and current_user context
        # Marked as TODO for integration test phase with FastAPI test client
        pass

    @pytest.mark.asyncio
    async def test_approval_reason_is_stored(self):
        """Rejection reason is stored and returned in request details."""
        # This test requires actual DB and current_user context
        # Marked as TODO for integration test phase with FastAPI test client
        pass
