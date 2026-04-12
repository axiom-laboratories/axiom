#!/bin/sh
# entrypoint.sh - Fix volume ownership before dropping to appuser
# This ensures mounted volumes (like secrets-data) are writable by appuser

# Fix ownership of /app/secrets volume (may be mounted and owned by root)
if [ -d /app/secrets ]; then
    chown -R appuser:appuser /app/secrets 2>/dev/null || true
fi

# Execute the given command as appuser
# Note: This script should be run as root, and will drop privileges
exec su appuser -c "exec $*"
