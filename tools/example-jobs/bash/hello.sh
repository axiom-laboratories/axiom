#!/usr/bin/env bash
set -euo pipefail

echo "=== Axiom Hello-World (Bash) ==="
echo "Host:    $(hostname)"
echo "OS:      $(uname -sr)"
echo "Bash:    ${BASH_VERSION}"
echo "Time:    $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== PASS ==="
