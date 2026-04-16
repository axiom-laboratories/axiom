"""Unit tests for GateEvaluationService."""

import json
import pytest
from agent_service.services.gate_evaluation_service import GateEvaluationService


class TestResolveField:
    def test_resolve_field_simple_key(self):
        """Resolve top-level field."""
        data = {"exit_code": 0, "message": "ok"}
        found, value = GateEvaluationService.resolve_field(data, "exit_code")
        assert found is True
        assert value == 0

    def test_resolve_field_nested_path(self):
        """Resolve nested dot-path."""
        data = {"data": {"status": "ok", "count": 5}}
        found, value = GateEvaluationService.resolve_field(data, "data.status")
        assert found is True
        assert value == "ok"

    def test_resolve_field_deep_nesting(self):
        """Resolve deeply nested path."""
        data = {"a": {"b": {"c": "value"}}}
        found, value = GateEvaluationService.resolve_field(data, "a.b.c")
        assert found is True
        assert value == "value"

    def test_resolve_field_missing_top_level(self):
        """Missing field returns (False, None)."""
        data = {"exit_code": 0}
        found, value = GateEvaluationService.resolve_field(data, "missing")
        assert found is False
        assert value is None

    def test_resolve_field_missing_nested(self):
        """Missing nested field returns (False, None)."""
        data = {"data": {"status": "ok"}}
        found, value = GateEvaluationService.resolve_field(data, "data.missing")
        assert found is False
        assert value is None

    def test_resolve_field_null_value(self):
        """Null value is valid (found=True, value=None)."""
        data = {"value": None}
        found, value = GateEvaluationService.resolve_field(data, "value")
        assert found is True
        assert value is None


class TestEvaluateCondition:
    def test_evaluate_condition_eq_match(self):
        """Equality condition matches."""
        cond = {"field": "exit_code", "op": "eq", "value": 0}
        result = {"exit_code": 0}
        assert GateEvaluationService.evaluate_condition(cond, result) is True

    def test_evaluate_condition_eq_no_match(self):
        """Equality condition fails."""
        cond = {"field": "exit_code", "op": "eq", "value": 0}
        result = {"exit_code": 1}
        assert GateEvaluationService.evaluate_condition(cond, result) is False

    def test_evaluate_condition_neq(self):
        """Not-equal condition."""
        cond = {"field": "status", "op": "neq", "value": "error"}
        assert GateEvaluationService.evaluate_condition(cond, {"status": "ok"}) is True
        assert GateEvaluationService.evaluate_condition(cond, {"status": "error"}) is False

    def test_evaluate_condition_gt(self):
        """Greater-than condition."""
        cond = {"field": "count", "op": "gt", "value": 5}
        assert GateEvaluationService.evaluate_condition(cond, {"count": 10}) is True
        assert GateEvaluationService.evaluate_condition(cond, {"count": 5}) is False
        assert GateEvaluationService.evaluate_condition(cond, {"count": 3}) is False

    def test_evaluate_condition_lt(self):
        """Less-than condition."""
        cond = {"field": "count", "op": "lt", "value": 5}
        assert GateEvaluationService.evaluate_condition(cond, {"count": 3}) is True
        assert GateEvaluationService.evaluate_condition(cond, {"count": 5}) is False
        assert GateEvaluationService.evaluate_condition(cond, {"count": 10}) is False

    def test_evaluate_condition_contains(self):
        """Contains condition."""
        cond = {"field": "message", "op": "contains", "value": "error"}
        assert GateEvaluationService.evaluate_condition(cond, {"message": "an error occurred"}) is True
        assert GateEvaluationService.evaluate_condition(cond, {"message": "success"}) is False

    def test_evaluate_condition_exists(self):
        """Exists condition."""
        cond = {"field": "flag", "op": "exists", "value": None}
        assert GateEvaluationService.evaluate_condition(cond, {"flag": True}) is True
        assert GateEvaluationService.evaluate_condition(cond, {"flag": False}) is True  # False is still present
        assert GateEvaluationService.evaluate_condition(cond, {"flag": None}) is True  # Null is present
        assert GateEvaluationService.evaluate_condition(cond, {"other": "value"}) is False

    def test_evaluate_condition_missing_field(self):
        """Condition fails for missing field."""
        cond = {"field": "missing", "op": "eq", "value": 0}
        assert GateEvaluationService.evaluate_condition(cond, {"exit_code": 0}) is False

    def test_evaluate_condition_type_mismatch(self):
        """Type mismatch on comparison returns False gracefully."""
        cond = {"field": "count", "op": "gt", "value": 5}
        result = {"count": "not_a_number"}
        assert GateEvaluationService.evaluate_condition(cond, result) is False


class TestEvaluateConditions:
    def test_evaluate_conditions_all_match(self):
        """All conditions must match (AND logic)."""
        conditions = [
            {"field": "exit_code", "op": "eq", "value": 0},
            {"field": "message", "op": "contains", "value": "success"}
        ]
        result = {"exit_code": 0, "message": "job success"}
        assert GateEvaluationService.evaluate_conditions(conditions, result) is True

    def test_evaluate_conditions_one_fails(self):
        """Fails if any condition fails."""
        conditions = [
            {"field": "exit_code", "op": "eq", "value": 0},
            {"field": "message", "op": "contains", "value": "success"}
        ]
        result = {"exit_code": 1, "message": "job success"}
        assert GateEvaluationService.evaluate_conditions(conditions, result) is False

    def test_evaluate_conditions_empty_list(self):
        """Empty conditions list (no conditions to match) returns True."""
        assert GateEvaluationService.evaluate_conditions([], {}) is True


class TestEvaluateIfGate:
    def test_evaluate_if_gate_true_branch(self):
        """IF gate evaluates true branch."""
        config = json.dumps({
            "branches": {
                "true": [{"field": "status", "op": "eq", "value": "ok"}],
                "false": []
            }
        })
        result = {"status": "ok"}
        branch, error = GateEvaluationService.evaluate_if_gate(config, result)
        assert branch == "true"
        assert error is None

    def test_evaluate_if_gate_false_branch(self):
        """IF gate evaluates false branch when true doesn't match."""
        config = json.dumps({
            "branches": {
                "true": [{"field": "status", "op": "eq", "value": "ok"}],
                "false": [{"field": "status", "op": "eq", "value": "error"}]
            }
        })
        result = {"status": "error"}
        branch, error = GateEvaluationService.evaluate_if_gate(config, result)
        assert branch == "false"
        assert error is None

    def test_evaluate_if_gate_no_match(self):
        """IF gate returns error if no branch matches."""
        config = json.dumps({
            "branches": {
                "true": [{"field": "status", "op": "eq", "value": "ok"}],
                "false": [{"field": "status", "op": "eq", "value": "error"}]
            }
        })
        result = {"status": "unknown"}
        branch, error = GateEvaluationService.evaluate_if_gate(config, result)
        assert branch is None
        assert error is not None

    def test_evaluate_if_gate_malformed_config(self):
        """IF gate handles malformed config_json gracefully."""
        config = "not valid json"
        result = {"status": "ok"}
        branch, error = GateEvaluationService.evaluate_if_gate(config, result)
        assert branch is None
        assert error is not None
