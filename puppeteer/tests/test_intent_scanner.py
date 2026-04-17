import pytest
import os
import sys
import io
from unittest.mock import patch

# Try to import intent_scanner; skip gracefully if not available
# This is an agent skill from toms_home/.agents/skills/interrogate-features/ that may not be in test environment
try:
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.agent/skills/interrogate-features/scripts"))
    if script_path not in sys.path:
        sys.path.append(script_path)
    import intent_scanner
except ImportError:
    intent_scanner = None
    pytest.skip("intent_scanner skill not available in test environment (agent skill from toms_home/.agents/skills/interrogate-features/)", allow_module_level=True)

def test_scan_file(tmp_path):
    test_file = tmp_path / "test_api.py"
    test_file.write_text('''
"""Module for testing."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/status")
def get_status():
    """Returns the status."""
    return {"status": "ok"}

class UserProfile:
    """Represents a user."""
    id: int
''')

    # Capture stdout
    f = io.StringIO()
    with patch('sys.stdout', f):
        intent_scanner.scan_file(str(test_file))
    
    output = f.getvalue()
    assert "[DOC] MODULE INTENT: Module for testing." in output
    assert "[API] ROUTE: GET /status -> 'get_status'" in output
    assert "Ref: Returns the status." in output
    assert "[MODEL] MODEL: UserProfile" in output
    assert "Desc: Represents a user." in output
