"""Unit tests for core response models (ActionResponse, PaginatedResponse[T], ErrorResponse)."""

import pytest
import json
from pydantic import ValidationError

from puppeteer.agent_service.models import ActionResponse, PaginatedResponse, ErrorResponse


class TestActionResponse:
    """Test ActionResponse model with all 8 status values."""

    @pytest.mark.parametrize("status", [
        "acknowledged", "cancelled", "revoked", "approved",
        "deleted", "updated", "created", "enabled", "disabled"
    ])
    def test_action_response_all_statuses(self, status):
        """Verify all 8 Literal values are accepted without validation error."""
        ar = ActionResponse(status=status, resource_type="job", resource_id="123")
        assert ar.status == status
        assert ar.resource_type == "job"
        assert ar.resource_id == "123"

    def test_action_response_invalid_status(self):
        """Verify Literal validation rejects typos and invalid status values."""
        with pytest.raises(ValidationError) as exc_info:
            ActionResponse(status="cancelledd", resource_type="job", resource_id="123")
        assert "Input should be" in str(exc_info.value)

    def test_action_response_serialization(self):
        """Verify JSON roundtrip preserves all fields including resource_id union."""
        ar = ActionResponse(status="created", resource_type="job", resource_id="456")
        json_str = ar.model_dump_json()
        parsed = ActionResponse.model_validate_json(json_str)
        assert parsed.resource_id == "456"
        assert parsed.status == "created"

    def test_action_response_optional_message(self):
        """Verify message field defaults to None."""
        ar = ActionResponse(status="updated", resource_type="node", resource_id=789)
        assert ar.message is None

    def test_action_response_with_message(self):
        """Verify message field stores provided value."""
        ar = ActionResponse(
            status="approved",
            resource_type="signature",
            resource_id="sig-123",
            message="Job approved by admin"
        )
        assert ar.message == "Job approved by admin"

    def test_action_response_resource_id_as_int(self):
        """Verify resource_id accepts both str and int."""
        ar_int = ActionResponse(status="deleted", resource_type="job", resource_id=999)
        assert ar_int.resource_id == 999
        assert isinstance(ar_int.resource_id, int)

    def test_action_response_from_orm(self):
        """Verify from_attributes=True allows ORM object construction."""
        # Simulate ORM object
        class MockORM:
            status = "acknowledged"
            resource_type = "node"
            resource_id = "node-1"
            message = "Node acknowledged"

        ar = ActionResponse.model_validate(MockORM())
        assert ar.status == "acknowledged"
        assert ar.resource_id == "node-1"


class TestPaginatedResponse:
    """Test PaginatedResponse[T] generic model."""

    def test_paginated_response_generic_with_string(self):
        """Test Generic[T] with simple string type."""
        pr = PaginatedResponse[str](items=["a", "b"], total=2, page=1, page_size=10)
        assert pr.items == ["a", "b"]
        assert pr.total == 2
        assert pr.page == 1
        assert pr.page_size == 10

    def test_paginated_response_generic_with_dict(self):
        """Test Generic[T] with dict items."""
        items = [{"id": 1, "name": "job1"}, {"id": 2, "name": "job2"}]
        pr = PaginatedResponse[dict](items=items, total=2, page=1, page_size=10)
        assert len(pr.items) == 2
        assert pr.items[0]["id"] == 1

    def test_paginated_response_json_roundtrip(self):
        """Verify JSON serialization and deserialization."""
        pr = PaginatedResponse[str](items=["x", "y", "z"], total=3, page=2, page_size=3)
        json_str = pr.model_dump_json()
        data = json.loads(json_str)
        assert data["total"] == 3
        assert data["page"] == 2
        assert len(data["items"]) == 3

    def test_paginated_response_schema_generated(self):
        """Verify OpenAPI schema can be generated."""
        schema = PaginatedResponse[str].model_json_schema()
        assert "properties" in schema
        assert "items" in schema["properties"]
        assert "total" in schema["properties"]
        assert "page" in schema["properties"]
        assert "page_size" in schema["properties"]

    def test_paginated_response_empty_items(self):
        """Verify empty items list is valid."""
        pr = PaginatedResponse[str](items=[], total=0, page=1, page_size=10)
        assert pr.items == []
        assert pr.total == 0

    def test_paginated_response_multiple_pages(self):
        """Verify pagination fields work correctly across pages."""
        pr1 = PaginatedResponse[str](items=["a", "b"], total=5, page=1, page_size=2)
        pr2 = PaginatedResponse[str](items=["c", "d"], total=5, page=2, page_size=2)
        pr3 = PaginatedResponse[str](items=["e"], total=5, page=3, page_size=2)
        assert pr1.page == 1
        assert pr2.page == 2
        assert pr3.page == 3

    def test_paginated_response_from_orm(self):
        """Verify from_attributes=True allows construction from ORM."""
        class MockORM:
            items = [{"guid": "123"}]
            total = 1
            page = 1
            page_size = 50

        pr = PaginatedResponse.model_validate(MockORM())
        assert pr.total == 1
        assert len(pr.items) == 1


class TestErrorResponse:
    """Test ErrorResponse model."""

    def test_error_response_creation(self):
        """Verify basic ErrorResponse creation."""
        er = ErrorResponse(detail="Not found", status_code=404)
        assert er.detail == "Not found"
        assert er.status_code == 404

    def test_error_response_serialization(self):
        """Verify JSON roundtrip."""
        er = ErrorResponse(detail="Unauthorized", status_code=401)
        json_str = er.model_dump_json()
        parsed = ErrorResponse.model_validate_json(json_str)
        assert parsed.detail == "Unauthorized"
        assert parsed.status_code == 401

    def test_error_response_various_codes(self):
        """Verify different HTTP status codes."""
        for code in [400, 401, 403, 404, 500, 502, 503]:
            er = ErrorResponse(detail=f"Error {code}", status_code=code)
            assert er.status_code == code

    def test_error_response_long_detail(self):
        """Verify detail field can hold long error messages."""
        long_msg = "This is a very long error message " * 10
        er = ErrorResponse(detail=long_msg, status_code=400)
        assert len(er.detail) > 100

    def test_error_response_from_orm(self):
        """Verify from_attributes=True allows ORM construction."""
        class MockORM:
            detail = "Database error"
            status_code = 500

        er = ErrorResponse.model_validate(MockORM())
        assert er.detail == "Database error"
        assert er.status_code == 500


class TestCoreModelsConfiguration:
    """Test shared configuration across core models."""

    def test_action_response_from_attributes_config(self):
        """Verify ActionResponse has ConfigDict(from_attributes=True)."""
        assert ActionResponse.model_config.get("from_attributes") is True

    def test_paginated_response_from_attributes_config(self):
        """Verify PaginatedResponse has ConfigDict(from_attributes=True)."""
        assert PaginatedResponse.model_config.get("from_attributes") is True

    def test_error_response_from_attributes_config(self):
        """Verify ErrorResponse has ConfigDict(from_attributes=True)."""
        assert ErrorResponse.model_config.get("from_attributes") is True

    def test_models_have_field_descriptions(self):
        """Verify Field descriptions are present for documentation."""
        ar_schema = ActionResponse.model_json_schema()
        # Check that description exists in schema properties
        assert "description" in ar_schema["properties"]["status"]
        assert "description" in ar_schema["properties"]["resource_type"]

    def test_paginated_response_has_examples(self):
        """Verify PaginatedResponse includes json_schema_extra examples."""
        pr_schema = PaginatedResponse[str].model_json_schema()
        assert "properties" in pr_schema
        # Verify items field exists
        assert "items" in pr_schema["properties"]
