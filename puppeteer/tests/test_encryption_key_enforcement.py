"""
Test suite for ENCRYPTION_KEY hard requirement enforcement.

Tests cover:
- ENCRYPTION_KEY must be present in environment at module load time
- Missing ENCRYPTION_KEY raises RuntimeError immediately
- Error message includes actionable Fernet key generation command
- When ENCRYPTION_KEY is set, module loads successfully
"""

import pytest
import os
import importlib
from unittest.mock import patch


class TestEncryptionKeyRequired:
    """Test ENCRYPTION_KEY hard requirement (EE-06)."""

    def test_encryption_key_required_at_module_load(self):
        """ENCRYPTION_KEY environment variable is required at module load time.

        Attempting to import security.py with missing ENCRYPTION_KEY raises RuntimeError.
        """
        # Mock os.getenv to return None for ENCRYPTION_KEY
        with patch.dict(os.environ, {}, clear=False):
            # Remove ENCRYPTION_KEY from environment
            if "ENCRYPTION_KEY" in os.environ:
                del os.environ["ENCRYPTION_KEY"]

            # Attempt to reload security module should raise RuntimeError
            import agent_service.security as security_module
            with pytest.raises(RuntimeError, match="ENCRYPTION_KEY environment variable is required"):
                # Re-execute the module-level code by calling _load_or_generate_encryption_key()
                security_module._load_or_generate_encryption_key()

    def test_encryption_key_absent_raises_runtime_error(self):
        """_load_or_generate_encryption_key() raises RuntimeError when ENCRYPTION_KEY is absent."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove ENCRYPTION_KEY from environment
            if "ENCRYPTION_KEY" in os.environ:
                del os.environ["ENCRYPTION_KEY"]

            import agent_service.security as security_module

            with pytest.raises(RuntimeError) as exc_info:
                security_module._load_or_generate_encryption_key()

            assert "ENCRYPTION_KEY environment variable is required" in str(exc_info.value)

    def test_encryption_key_error_message_includes_generation_command(self):
        """Error message includes Fernet key generation one-liner when ENCRYPTION_KEY absent."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove ENCRYPTION_KEY from environment
            if "ENCRYPTION_KEY" in os.environ:
                del os.environ["ENCRYPTION_KEY"]

            import agent_service.security as security_module

            with pytest.raises(RuntimeError) as exc_info:
                security_module._load_or_generate_encryption_key()

            error_msg = str(exc_info.value)
            # Verify key generation command is in the error message
            assert "python -c" in error_msg
            assert "Fernet.generate_key()" in error_msg

    def test_encryption_key_loads_successfully_when_set(self):
        """When ENCRYPTION_KEY environment variable is set, module loads successfully."""
        # Use a valid Fernet key for testing
        from cryptography.fernet import Fernet
        valid_key = Fernet.generate_key().decode()

        with patch.dict(os.environ, {"ENCRYPTION_KEY": valid_key}):
            import agent_service.security as security_module

            # Should not raise an exception
            result = security_module._load_or_generate_encryption_key()

            # Result should be bytes (Fernet key format)
            assert isinstance(result, bytes)
            assert result == valid_key.encode()
