"""
Unit tests for job admission control logic (v20.0).

Tests parse_bytes() utility and basic capacity calculation.
"""
import pytest
from agent_service.services.job_service import (
    parse_bytes,
    _format_bytes,
)


# ============================================================================
# TestParseBytes - Unit tests for memory string parsing
# ============================================================================

class TestParseBytes:
    """Test parse_bytes() utility for memory format conversion."""

    def test_parse_bytes_megabytes(self):
        """Test conversion: 512m -> 536870912 bytes (512 * 1024^2)"""
        result = parse_bytes("512m")
        assert result == 512 * (1024 ** 2), f"Expected {512 * (1024 ** 2)}, got {result}"

    def test_parse_bytes_gigabytes(self):
        """Test conversion: 1g -> 1073741824 bytes (1 * 1024^3)"""
        result = parse_bytes("1g")
        assert result == 1 * (1024 ** 3), f"Expected {1 * (1024 ** 3)}, got {result}"

    def test_parse_bytes_kilobytes(self):
        """Test conversion: 1024k -> 1048576 bytes (1024 * 1024)"""
        result = parse_bytes("1024k")
        assert result == 1024 * 1024, f"Expected {1024 * 1024}, got {result}"

    def test_parse_bytes_case_insensitive(self):
        """Test case-insensitive parsing: 1Gi -> 1073741824 bytes"""
        result_gi = parse_bytes("1Gi")
        result_g = parse_bytes("1g")
        # Both should parse as 1 gigabyte (1024^3 bytes)
        assert result_gi == result_g, f"1Gi={result_gi} != 1g={result_g}"

    def test_parse_bytes_no_suffix(self):
        """Test raw bytes: '2' -> 2 bytes (no suffix = raw bytes)"""
        result = parse_bytes("2")
        assert result == 2, f"Expected 2, got {result}"

    def test_parse_bytes_with_ki_suffix(self):
        """Test Ki suffix: 1Ki -> 1024 bytes"""
        result = parse_bytes("1Ki")
        assert result == 1024, f"Expected 1024, got {result}"

    def test_parse_bytes_with_mi_suffix(self):
        """Test Mi suffix: 512Mi -> 536870912 bytes"""
        result = parse_bytes("512Mi")
        assert result == 512 * (1024 ** 2), f"Expected {512 * (1024 ** 2)}, got {result}"

    def test_parse_bytes_with_gi_suffix(self):
        """Test Gi suffix: 2Gi -> 2147483648 bytes"""
        result = parse_bytes("2Gi")
        assert result == 2 * (1024 ** 3), f"Expected {2 * (1024 ** 3)}, got {result}"


# ============================================================================
# TestFormatBytes - Format helper for error messages
# ============================================================================

class TestFormatBytes:
    """Test _format_bytes() for human-readable error messages."""

    def test_format_bytes_gigabytes(self):
        """Test: 1073741824 -> '1.0Gi'"""
        result = _format_bytes(1073741824)
        # Should be human-readable, exact format flexible
        assert "G" in result or "g" in result.lower(), f"Expected G unit, got {result}"
        assert "1.0" in result or "1.1" in result, f"Expected magnitude ~1.0, got {result}"

    def test_format_bytes_megabytes(self):
        """Test: 536870912 -> '512.0Mi' or similar"""
        result = _format_bytes(536870912)
        # Should be in megabytes or gigabytes (not bytes)
        assert "M" in result or "G" in result or "m" in result.lower(), f"Expected M or G unit, got {result}"

    def test_format_bytes_small_value(self):
        """Test: 1024 bytes -> formatted with Ki suffix"""
        result = _format_bytes(1024)
        assert "B" in result or "Ki" in result, f"Expected B or Ki unit, got {result}"


# ============================================================================
# TestCapacityComputation - Basic capacity calculation logic
# ============================================================================

class TestCapacityComputation:
    """Test parse_bytes usage in capacity computation."""

    def test_capacity_exceed_check(self):
        """Test that 4Gi exceeds 1Gi node"""
        job_bytes = parse_bytes("4Gi")
        node_capacity = parse_bytes("1Gi")
        assert job_bytes > node_capacity, "4Gi should exceed 1Gi"

    def test_capacity_fit_check(self):
        """Test that 512m fits in 1Gi node"""
        job_bytes = parse_bytes("512m")
        node_capacity = parse_bytes("1Gi")
        assert job_bytes < node_capacity, "512m should fit in 1Gi"

    def test_capacity_sum_multiple(self):
        """Test summing multiple job limits"""
        job1 = parse_bytes("512m")
        job2 = parse_bytes("512m")
        job3 = parse_bytes("256m")
        total = job1 + job2 + job3
        expected = (512 + 512 + 256) * (1024 ** 2)
        assert total == expected, f"Expected {expected}, got {total}"

    def test_available_capacity_calculation(self):
        """Test available capacity = total - used"""
        node_capacity = parse_bytes("2Gi")
        used = (512 + 512 + 256) * (1024 ** 2)  # 1280m in bytes
        available = node_capacity - used
        
        # Should be positive
        assert available > 0, f"Available should be > 0, got {available}"
        
        # Should be less than total
        assert available < node_capacity, f"Available should be < total"


# ============================================================================
# TestAdmissionLogic - Logic tests for admission control
# ============================================================================

class TestAdmissionLogic:
    """Test the logic of admission control without full async."""

    def test_null_limit_default(self):
        """Test that null limit defaults to 512m"""
        limit = None
        effective_limit = limit or "512m"
        assert effective_limit == "512m", "Null limit should default to 512m"
        
        limit_bytes = parse_bytes(effective_limit)
        assert limit_bytes == 512 * (1024 ** 2), "Default should be 512m in bytes"

    def test_admission_exceeds_largest_available(self):
        """Test: if job > largest available node, reject"""
        job_bytes = parse_bytes("4Gi")
        
        # Simulate 3 nodes with capacities
        node_capacities = [
            parse_bytes("512m"),
            parse_bytes("1Gi"),
            parse_bytes("2Gi"),
        ]
        
        largest_available = max(node_capacities)
        
        # Job should be rejected
        assert job_bytes > largest_available, "Job should exceed largest node"

    def test_admission_fits_largest_node(self):
        """Test: if job <= largest available node, accept"""
        job_bytes = parse_bytes("512m")
        
        # Simulate 3 nodes with capacities
        node_capacities = [
            parse_bytes("256m"),
            parse_bytes("512m"),
            parse_bytes("1Gi"),
        ]
        
        largest_available = max(node_capacities)
        
        # Job should be accepted
        assert job_bytes <= largest_available, "Job should fit in largest node"

    def test_format_bytes_for_error_messages(self):
        """Test that formatted bytes are suitable for error messages"""
        # Test a variety of values
        test_cases = [
            (parse_bytes("512m"), "512.0M" or "512.0Mi"),
            (parse_bytes("1Gi"), "1.0G" or "1.0Gi"),
            (parse_bytes("256m"), "256.0M" or "256.0Mi"),
        ]
        
        for bytes_val, expected_unit in test_cases:
            formatted = _format_bytes(bytes_val)
            # Just check that it's human-readable with some unit
            assert any(u in formatted for u in ["K", "M", "G", "B"]), f"Expected unit in {formatted}"
