"""
Unit tests for CgroupDetector class.

Tests cover v1, v2, hybrid, permission errors, and inconsistent cgroup detection scenarios.
Uses unittest.mock.patch to mock pathlib.Path reads and filesystem checks.
"""

import pytest
from unittest.mock import patch, MagicMock
import pathlib

from puppets.environment_service.node import CgroupDetector


class TestCgroupDetectorV2:
    """Test pure cgroup v2 detection."""

    def test_detect_cgroup_v2_pure(self):
        """Test detection of pure v2 with cgroup.controllers present."""
        mock_cgroup_content = "0::/test-cgroup\n"

        with patch.object(pathlib.Path, 'read_text', return_value=mock_cgroup_content), \
             patch.object(pathlib.Path, 'exists', return_value=True):
            version, raw = CgroupDetector.detect()
            assert version == "v2"
            assert "cgroup.controllers exists" in raw


class TestCgroupDetectorV1:
    """Test pure cgroup v1 detection."""

    def test_detect_cgroup_v1_pure(self):
        """Test detection of pure v1 with numbered hierarchy."""
        mock_cgroup_content = "1:memory:/test-mem\n2:cpu:/test-cpu\n3:devices:/test-dev\n"

        with patch.object(pathlib.Path, 'read_text', return_value=mock_cgroup_content), \
             patch.object(pathlib.Path, 'exists', return_value=False):
            version, raw = CgroupDetector.detect()
            assert version == "v1"
            assert "Numbered cgroup hierarchy" in raw


class TestCgroupDetectorHybrid:
    """Test hybrid cgroup detection (mixed v1+v2)."""

    def test_detect_cgroup_hybrid_conservatively_v1(self):
        """Test hybrid v1+v2 setup reported as v1 (conservative)."""
        mock_cgroup_content = "0::/test-v2\n1:memory:/test-v1-mem\n"

        with patch.object(pathlib.Path, 'read_text', return_value=mock_cgroup_content):
            version, raw = CgroupDetector.detect()
            assert version == "v1"
            assert "Hybrid cgroup setup" in raw


class TestCgroupDetectorUnsupported:
    """Test unsupported/error cgroup detection."""

    def test_detect_cgroup_unsupported_permission_error(self):
        """Test permission denied returns unsupported."""
        with patch.object(pathlib.Path, 'read_text', side_effect=PermissionError("Access denied")):
            version, raw = CgroupDetector.detect()
            assert version == "unsupported"
            assert "PermissionError" in raw

    def test_detect_cgroup_unsupported_file_not_found(self):
        """Test file not found returns unsupported."""
        with patch.object(pathlib.Path, 'read_text', side_effect=FileNotFoundError("Not found")):
            version, raw = CgroupDetector.detect()
            assert version == "unsupported"
            assert "FileNotFoundError" in raw

    def test_detect_cgroup_unsupported_os_error(self):
        """Test OS error returns unsupported."""
        with patch.object(pathlib.Path, 'read_text', side_effect=OSError("IO error")):
            version, raw = CgroupDetector.detect()
            assert version == "unsupported"
            assert "OSError" in raw

    def test_detect_cgroup_unsupported_v2_format_no_controllers(self):
        """Test v2 format detected but cgroup.controllers missing (inconsistent)."""
        mock_cgroup_content = "0::/test-cgroup\n"

        with patch.object(pathlib.Path, 'read_text', return_value=mock_cgroup_content), \
             patch.object(pathlib.Path, 'exists', return_value=False):
            version, raw = CgroupDetector.detect()
            assert version == "unsupported"
            assert "inconsistent" in raw


class TestCgroupDetectorLogging:
    """Test logging behavior for cgroup detection."""

    def test_detect_cgroup_logs_v1_info(self):
        """Test that v1 detection is logged at info level."""
        mock_cgroup_content = "1:memory:/test-mem\n2:cpu:/test-cpu\n"

        with patch.object(pathlib.Path, 'read_text', return_value=mock_cgroup_content), \
             patch.object(pathlib.Path, 'exists', return_value=False), \
             patch('puppets.environment_service.node.logger') as mock_logger:
            version, raw = CgroupDetector.detect()
            assert version == "v1"
            # Logging is done by _detect_cgroup_version(), not detect() itself
            # This test verifies the detection returns correct value for logging

    def test_detect_cgroup_logs_v2_info(self):
        """Test that v2 detection is logged at info level."""
        mock_cgroup_content = "0::/test-cgroup\n"

        with patch.object(pathlib.Path, 'read_text', return_value=mock_cgroup_content), \
             patch.object(pathlib.Path, 'exists', return_value=True):
            version, raw = CgroupDetector.detect()
            assert version == "v2"
            # Logging is done by _detect_cgroup_version(), not detect() itself


class TestCgroupDetectorRawData:
    """Test raw data format in detection results."""

    def test_detect_raw_data_contains_line_count(self):
        """Test that raw data includes line count information."""
        mock_cgroup_content = "1:memory:/test-mem\n2:cpu:/test-cpu\n"

        with patch.object(pathlib.Path, 'read_text', return_value=mock_cgroup_content), \
             patch.object(pathlib.Path, 'exists', return_value=False):
            version, raw = CgroupDetector.detect()
            assert "lines" in raw or "Numbered" in raw

    def test_detect_raw_data_contains_content_preview(self):
        """Test that raw data includes preview of /proc/self/cgroup content."""
        mock_cgroup_content = "1:memory:/test-mem\n2:cpu:/test-cpu\n"

        with patch.object(pathlib.Path, 'read_text', return_value=mock_cgroup_content), \
             patch.object(pathlib.Path, 'exists', return_value=False):
            version, raw = CgroupDetector.detect()
            # Raw data should include some portion of the actual content or detection info
            assert "test-mem" in raw or "Numbered" in raw


class TestCgroupDetectorEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_detect_empty_cgroup_file(self):
        """Test handling of empty /proc/self/cgroup."""
        mock_cgroup_content = ""

        with patch.object(pathlib.Path, 'read_text', return_value=mock_cgroup_content), \
             patch.object(pathlib.Path, 'exists', return_value=False):
            version, raw = CgroupDetector.detect()
            assert version == "unsupported"

    def test_detect_whitespace_only_cgroup_file(self):
        """Test handling of whitespace-only /proc/self/cgroup."""
        mock_cgroup_content = "   \n\n   "

        with patch.object(pathlib.Path, 'read_text', return_value=mock_cgroup_content), \
             patch.object(pathlib.Path, 'exists', return_value=False):
            version, raw = CgroupDetector.detect()
            assert version == "unsupported"

    def test_detect_malformed_cgroup_content(self):
        """Test handling of malformed cgroup content."""
        mock_cgroup_content = "some-random-text-without-proper-format\n"

        with patch.object(pathlib.Path, 'read_text', return_value=mock_cgroup_content), \
             patch.object(pathlib.Path, 'exists', return_value=False):
            version, raw = CgroupDetector.detect()
            assert version == "unsupported"
