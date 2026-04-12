#!/usr/bin/env python3
"""
Entrypoint script for Master of Puppets containers.

Fixes volume ownership to appuser before dropping privileges and executing the main process.
"""

import os
import sys
import pwd
import subprocess
import shutil

def fix_volume_permissions():
    """Fix ownership of /app/secrets volume to appuser."""
    secrets_path = "/app/secrets"
    if os.path.isdir(secrets_path):
        try:
            # Get appuser UID/GID
            appuser = pwd.getpwnam("appuser")
            uid = appuser.pw_uid
            gid = appuser.pw_gid

            # Recursively chown the directory
            for root, dirs, files in os.walk(secrets_path):
                os.chown(root, uid, gid)
                for d in dirs:
                    os.chown(os.path.join(root, d), uid, gid)
                for f in files:
                    os.chown(os.path.join(root, f), uid, gid)

            print(f"✓ Fixed {secrets_path} ownership to appuser:appuser", file=sys.stderr)
        except Exception as e:
            print(f"⚠ Failed to fix {secrets_path} ownership: {e}", file=sys.stderr)


def drop_privileges():
    """Drop privileges from root to appuser."""
    try:
        appuser = pwd.getpwnam("appuser")
        os.setgid(appuser.pw_gid)
        os.setuid(appuser.pw_uid)
        print("✓ Dropped privileges to appuser", file=sys.stderr)
    except Exception as e:
        print(f"✗ Failed to drop privileges: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Fix permissions and execute the main command."""
    if len(sys.argv) < 2:
        print("Usage: entrypoint.py <command> [args...]", file=sys.stderr)
        sys.exit(1)

    fix_volume_permissions()

    # Drop privileges
    drop_privileges()

    # Execute the main command (replace this process with it)
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
