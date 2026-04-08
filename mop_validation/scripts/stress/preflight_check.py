#!/usr/bin/env python3
"""
Preflight validation script for stress testing.
Runs as a dispatched job on target node to validate cgroup support, resource controllers,
and memory limits enforcement.

Output: JSON with per-check pass/fail breakdown on first line, followed by human summary.
Exit codes:
  0 = all checks pass
  1 = at least one check fails
"""

import json
import os
import sys
from pathlib import Path


def read_file(path: str) -> str:
    """Safely read file content, return empty string if not found."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def detect_cgroup_version() -> str:
    """Detect cgroup version (v1, v2, or unsupported)."""
    # Check /proc/mounts for cgroup2 filesystem (v2)
    mounts = read_file("/proc/mounts")
    if "cgroup2" in mounts:
        return "v2"

    # Check /proc/mounts for cgroup filesystem (v1)
    if "cgroup " in mounts:
        return "v1"

    return "unsupported"


def check_cpu_controller() -> bool:
    """Check if CPU controller is enabled."""
    cgroup_version = detect_cgroup_version()

    if cgroup_version == "v2":
        # v2: check /sys/fs/cgroup/cpu.max exists
        return Path("/sys/fs/cgroup/cpu.max").exists()
    elif cgroup_version == "v1":
        # v1: check /sys/fs/cgroup/cpu directory exists
        return Path("/sys/fs/cgroup/cpu").exists()

    return False


def check_memory_controller() -> bool:
    """Check if memory controller is enabled."""
    cgroup_version = detect_cgroup_version()

    if cgroup_version == "v2":
        # v2: check /sys/fs/cgroup/memory.max exists
        return Path("/sys/fs/cgroup/memory.max").exists()
    elif cgroup_version == "v1":
        # v1: check /sys/fs/cgroup/memory/memory.limit_in_bytes exists
        return Path("/sys/fs/cgroup/memory/memory.limit_in_bytes").exists()

    return False


def check_memory_limit_applied() -> bool:
    """Check if memory limit is applied to own container."""
    cgroup_version = detect_cgroup_version()

    if cgroup_version == "v2":
        # v2: read /sys/fs/cgroup/memory.max
        limit_str = read_file("/sys/fs/cgroup/memory.max")
        if limit_str and limit_str != "max":
            try:
                limit = int(limit_str)
                return limit > 0 and limit < 9223372036854775807  # < max int64
            except ValueError:
                return False
    elif cgroup_version == "v1":
        # v1: read /sys/fs/cgroup/memory/memory.limit_in_bytes
        limit_str = read_file("/sys/fs/cgroup/memory/memory.limit_in_bytes")
        if limit_str:
            try:
                limit = int(limit_str)
                # Check if limit is not the default unlimited value
                # In v1, unlimited is typically 9223372036854775807 (max int64)
                return 0 < limit < 9223372036854775807
            except ValueError:
                return False

    return False


def main():
    """Run all checks and output results."""
    cgroup_version = detect_cgroup_version()

    checks = {
        "cgroup_version_detected": cgroup_version != "unsupported",
        "cpu_controller_enabled": check_cpu_controller(),
        "memory_controller_enabled": check_memory_controller(),
        "memory_limit_applied": check_memory_limit_applied(),
    }

    all_pass = all(checks.values())

    # Output JSON
    result = {
        "type": "preflight_check",
        "cgroup_version": cgroup_version,
        "checks": checks,
        "pass": all_pass,
    }

    print(json.dumps(result))

    # Output human summary
    if all_pass:
        summary = f"PASS: All cgroup checks passed ({cgroup_version}, cpu+memory enabled, limit applied)"
        print(summary)
    else:
        failed = [k for k, v in checks.items() if not v]
        summary = f"FAIL: Missing {', '.join(failed)}"
        print(summary)

    # Exit code
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
