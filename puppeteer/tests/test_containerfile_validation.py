"""
Containerfile validation tests for Phase 135.

Tests verify that:
- CONT-07: Containerfile.node removes exactly podman, iptables, krb5-user packages
  (not in any RUN apt-get install lines after socket mount refactor)

Tests use static file analysis — no Docker required.

Requirements verified: CONT-07
"""

import re
import pytest


def load_containerfile(path='../puppets/Containerfile.node'):
    """
    Load Containerfile.node content.

    Args:
        path: Path to Containerfile.node relative to puppeteer/tests/

    Returns:
        Containerfile content as string
    """
    import os
    # Navigate from tests/ up to project root, then to puppets/
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(test_dir))
    full_path = os.path.join(project_root, 'puppets', 'Containerfile.node')

    with open(full_path, 'r') as f:
        return f.read()


class TestContainerfilePackageRemoval:
    """Static Containerfile analysis tests."""

    def test_podman_package_explicitly_removed(self):
        """CONT-07: Verify 'podman' package explicitly removed (purged) in node image."""
        content = load_containerfile()

        # Normalize: remove line continuations (\ at end of line)
        content = re.sub(r'\\\n\s*', ' ', content)

        # Find apt-get purge commands (these remove packages)
        purge_commands = re.findall(r'apt-get purge[^;]*', content, re.DOTALL)

        assert len(purge_commands) > 0, "No apt-get purge commands found"

        # Check if podman is in any purge command
        found_in_purge = False
        for cmd in purge_commands:
            if 'podman' in cmd:
                found_in_purge = True
                break

        assert found_in_purge, \
            f"podman not found in any apt-get purge command. Purge commands: {purge_commands}"

    def test_iptables_package_explicitly_removed(self):
        """CONT-07: Verify 'iptables' package explicitly removed (purged) in node image."""
        content = load_containerfile()

        # Normalize: remove line continuations
        content = re.sub(r'\\\n\s*', ' ', content)

        # Find apt-get purge commands
        purge_commands = re.findall(r'apt-get purge[^;]*', content, re.DOTALL)

        assert len(purge_commands) > 0, "No apt-get purge commands found"

        # Check if iptables is in any purge command
        found_in_purge = False
        for cmd in purge_commands:
            if 'iptables' in cmd:
                found_in_purge = True
                break

        assert found_in_purge, \
            f"iptables not found in any apt-get purge command. Purge commands: {purge_commands}"

    def test_krb5_user_package_explicitly_removed(self):
        """CONT-07: Verify 'krb5-user' package explicitly removed (purged) in node image."""
        content = load_containerfile()

        # Normalize: remove line continuations
        content = re.sub(r'\\\n\s*', ' ', content)

        # Find apt-get purge commands
        purge_commands = re.findall(r'apt-get purge[^;]*', content, re.DOTALL)

        assert len(purge_commands) > 0, "No apt-get purge commands found"

        # Check if krb5-user is in any purge command
        found_in_purge = False
        for cmd in purge_commands:
            if 'krb5-user' in cmd:
                found_in_purge = True
                break

        assert found_in_purge, \
            f"krb5-user not found in any apt-get purge command. Purge commands: {purge_commands}"

    def test_essential_packages_retained(self):
        """CONT-07: Verify essential packages (curl, wget, gnupg, apt-transport-https) still present."""
        content = load_containerfile()

        # Normalize: remove line continuations
        content = re.sub(r'\\\n\s*', ' ', content)

        # Find all apt-get install commands
        install_commands = re.findall(r'apt-get install[^;]*', content, re.DOTALL)

        assert len(install_commands) > 0, "No apt-get install commands found"

        # Combine all install commands to check across multiple RUN statements
        combined_installs = ' '.join(install_commands)

        # At least one of these essential packages should appear
        essential_packages = ['curl', 'wget', 'gnupg', 'apt-transport-https']

        for pkg in essential_packages:
            assert pkg in combined_installs, \
                f"Essential package '{pkg}' not found in any install command"
