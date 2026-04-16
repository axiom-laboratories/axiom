"""
GateEvaluationService — Logic for evaluating gate node conditions and routing decisions.

Handles IF_GATE branch routing based on condition evaluation against step result output.
Condition operators: eq, neq, gt, lt, contains, exists.
"""

import json
from typing import Dict, List, Optional, Tuple, Any


class GateEvaluationService:
    """Service for evaluating gate node conditions and routing."""

    @staticmethod
    def resolve_field(data: Dict, path: str) -> Tuple[bool, Any]:
        """
        Resolve a dot-path field in a data dictionary.

        Examples:
        - "exit_code" → data["exit_code"]
        - "data.status" → data["data"]["status"]
        - "result.details.code" → data["result"]["details"]["code"]

        Args:
            data: Dictionary to traverse
            path: Dot-separated path (e.g., "exit_code", "data.status")

        Returns:
            Tuple of (found: bool, value: Any). found=True if path exists, False otherwise.
            value is the resolved value or None if not found.
        """
        if not path:
            return False, None

        keys = path.split(".")
        current = data

        for key in keys:
            if not isinstance(current, dict):
                return False, None

            if key not in current:
                return False, None

            current = current[key]

        return True, current

    @staticmethod
    def evaluate_condition(condition: Dict, result: Dict) -> bool:
        """
        Evaluate a single condition against step result.

        Condition format:
        {
            "field": "path.to.field",
            "op": "eq|neq|gt|lt|contains|exists",
            "value": <comparison value>
        }

        Args:
            condition: Condition dict with field, op, value
            result: Step result dict to evaluate against

        Returns:
            True if condition matches, False otherwise.
        """
        field = condition.get("field", "")
        op = condition.get("op", "")
        value = condition.get("value")

        found, actual = GateEvaluationService.resolve_field(result, field)

        if not found:
            # Field doesn't exist
            if op == "exists":
                return False
            else:
                return False

        # Operators
        try:
            if op == "eq":
                return actual == value
            elif op == "neq":
                return actual != value
            elif op == "gt":
                return actual > value
            elif op == "lt":
                return actual < value
            elif op == "contains":
                return str(value) in str(actual)
            elif op == "exists":
                return True  # Field was found
            else:
                # Unknown operator
                return False
        except TypeError:
            # Type mismatch (e.g., comparing string to int with gt)
            return False

    @staticmethod
    def evaluate_conditions(conditions: List[Dict], result: Dict) -> bool:
        """
        Evaluate all conditions with AND logic.

        Args:
            conditions: List of condition dicts
            result: Step result dict

        Returns:
            True only if ALL conditions match.
        """
        if not conditions:
            # Empty condition list = always True
            return True

        for condition in conditions:
            if not GateEvaluationService.evaluate_condition(condition, result):
                return False

        return True

    @staticmethod
    def evaluate_if_gate(config_json: str, result: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Evaluate IF gate configuration to determine which branch to route to.

        Config format (in config_json string):
        {
            "branches": {
                "true": [
                    {"field": "exit_code", "op": "eq", "value": 0},
                    ...
                ],
                "false": [
                    {"field": "exit_code", "op": "neq", "value": 0},
                    ...
                ]
            }
        }

        Branches are evaluated in order: "true" first, then "false".
        Returns the first matching branch, or (None, error_msg) if no match.

        Args:
            config_json: JSON string containing branches config
            result: Step result dict to evaluate against

        Returns:
            Tuple of (branch_taken, error_message).
            branch_taken: "true" or "false" if a branch matched, None if no match.
            error_message: Error description if no branch matched, None if successful.
        """
        try:
            config = json.loads(config_json)
        except json.JSONDecodeError as e:
            return None, f"Invalid config_json: {str(e)}"

        branches = config.get("branches", {})
        if not branches:
            return None, "No branches in config"

        # Evaluate "true" branch first
        for branch_name in ["true", "false"]:
            conditions = branches.get(branch_name, [])
            if GateEvaluationService.evaluate_conditions(conditions, result):
                return branch_name, None

        # No branch matched
        return None, "No branch conditions matched"
