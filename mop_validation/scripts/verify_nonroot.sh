#!/bin/bash
#
# verify_nonroot.sh - Standalone verification script for non-root user configuration
#
# Verifies that all container processes run as UID 1000 and that /app and /app/secrets
# are owned by appuser:appuser. Useful for ops teams and manual validation.
#
# Requirements verified: CONT-01 (non-root user), CONT-06 (secrets volume ownership)
#

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'  # No Color

PASSED=0
FAILED=0

check_result() {
    local name=$1
    local expected=$2
    local actual=$3

    if [ "$expected" == "$actual" ]; then
        echo -e "${GREEN}✓${NC} $name: PASS"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $name: FAIL (expected: $expected, got: $actual)"
        ((FAILED++))
    fi
}

echo "=== Checking Non-Root User Configuration ==="
echo ""

# Check 1: Agent process UID (CONT-01)
echo "Checking Agent container..."
agent_uid=$(docker exec puppeteer-agent-1 ps -o uid=,comm= | grep python | awk '{print $1}' | head -1)
check_result "Agent process UID" "1000" "$agent_uid"

# Check 2: Model process UID (CONT-01)
echo "Checking Model container..."
model_uid=$(docker exec puppeteer-model-1 ps -o uid=,comm= | grep python | awk '{print $1}' | head -1)
check_result "Model process UID" "1000" "$model_uid"

# Check 3: Node process UID (CONT-01)
echo "Checking Node container..."
node_uid=$(docker exec node ps -o uid=,comm= | grep python | awk '{print $1}' | head -1)
check_result "Node process UID" "1000" "$node_uid"

# Check 4: Agent /app ownership (CONT-01)
echo "Checking Agent /app ownership..."
agent_app_owner=$(docker exec puppeteer-agent-1 stat -c %U:%G /app)
check_result "Agent /app ownership" "appuser:appuser" "$agent_app_owner"

# Check 5: Model /app ownership (CONT-01)
echo "Checking Model /app ownership..."
model_app_owner=$(docker exec puppeteer-model-1 stat -c %U:%G /app)
check_result "Model /app ownership" "appuser:appuser" "$model_app_owner"

# Check 6: Node /app ownership (CONT-01)
echo "Checking Node /app ownership..."
node_app_owner=$(docker exec node stat -c %U:%G /app)
check_result "Node /app ownership" "appuser:appuser" "$node_app_owner"

# Check 7: Secrets volume ownership (CONT-06)
echo "Checking secrets volume ownership..."
secrets_owner=$(docker exec puppeteer-agent-1 stat -c %U:%G /app/secrets)
check_result "Secrets volume ownership" "appuser:appuser" "$secrets_owner"

# Check 8: Volume write access (CONT-06)
echo "Checking secrets volume write access..."
test_file="/app/secrets/verify_nonroot_test_$RANDOM.txt"
if docker exec puppeteer-agent-1 sh -c "touch $test_file && rm $test_file" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Volume write access: PASS"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Volume write access: FAIL"
    ((FAILED++))
fi

echo ""
echo "=== Summary ==="
echo "Passed: $PASSED/8"
echo "Failed: $FAILED/8"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed${NC}"
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    exit 1
fi
