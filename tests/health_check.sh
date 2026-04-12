#!/bin/bash
# AutoOps — Quick Health Check Script
# Run this any time to verify your entire stack is working
#
# Usage:
#   ./health_check.sh https://your-api.execute-api.us-east-1.amazonaws.com/dev
#   ./health_check.sh  (reads from AUTOOPS_API_URL env var)

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

API_URL="${1:-$AUTOOPS_API_URL}"

if [ -z "$API_URL" ]; then
  echo -e "${RED}Error: No API URL provided${NC}"
  echo "Usage: ./health_check.sh https://xxx.execute-api.us-east-1.amazonaws.com/dev"
  echo "   or: export AUTOOPS_API_URL=https://... && ./health_check.sh"
  exit 1
fi

API_URL="${API_URL%/}"

echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════${NC}"
echo -e "${BOLD}  AutoOps — Stack Health Check${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════${NC}"
echo -e "  API: ${CYAN}${API_URL}${NC}"
echo ""

pass() { echo -e "  ${GREEN}✓${NC}  $1"; }
fail() { echo -e "  ${RED}✗${NC}  $1"; FAILED=1; }
info() { echo -e "  ${CYAN}→${NC}  $1"; }

FAILED=0

# ── Check 1: Health endpoint ──────────────────────────────────
info "Checking GET /health..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" --max-time 10)
if [ "$RESPONSE" = "200" ]; then
  pass "Health endpoint returned 200"
else
  fail "Health endpoint returned $RESPONSE (expected 200)"
fi

# ── Check 2: Items list ───────────────────────────────────────
info "Checking GET /items..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/items" --max-time 10)
if [ "$RESPONSE" = "200" ]; then
  pass "Items list returned 200"
elif [ "$RESPONSE" = "503" ]; then
  echo -e "  ${YELLOW}⚠${NC}  Items list returned 503 (DynamoDB throttle — alarm should fire)"
else
  fail "Items list returned $RESPONSE"
fi

# ── Check 3: Create item ──────────────────────────────────────
info "Checking POST /items..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_URL}/items" \
  -H "Content-Type: application/json" \
  -d '{"name":"HealthCheck","category":"test"}' \
  --max-time 10)
if [ "$RESPONSE" = "201" ]; then
  pass "Create item returned 201"
elif [ "$RESPONSE" = "503" ]; then
  echo -e "  ${YELLOW}⚠${NC}  Create item returned 503 (DynamoDB throttle)"
else
  fail "Create item returned $RESPONSE"
fi

# ── Check 4: 404 for unknown route ───────────────────────────
info "Checking 404 for unknown route..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/nonexistent" --max-time 10)
if [ "$RESPONSE" = "404" ]; then
  pass "Unknown route correctly returned 404"
else
  fail "Unknown route returned $RESPONSE (expected 404)"
fi

# ── Check 5: Response time ────────────────────────────────────
info "Checking response time..."
TOTAL_TIME=$(curl -s -o /dev/null -w "%{time_total}" "${API_URL}/health" --max-time 10)
TOTAL_MS=$(echo "$TOTAL_TIME * 1000" | bc 2>/dev/null || echo "?")
if (( $(echo "$TOTAL_TIME < 3.0" | bc -l) )); then
  pass "Response time: ${TOTAL_MS}ms (good)"
else
  echo -e "  ${YELLOW}⚠${NC}  Response time: ${TOTAL_MS}ms (slow — could indicate cold start)"
fi

# ── Summary ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}══════════════════════════════════════${NC}"
if [ "$FAILED" = "0" ]; then
  echo -e "  ${GREEN}${BOLD}Stack is healthy ✓${NC}"
  echo ""
  echo -e "  ${CYAN}Next steps:${NC}"
  echo -e "  → python tests/test_api.py --url ${API_URL}"
  echo -e "  → python tests/trigger_throttle.py --url ${API_URL}"
else
  echo -e "  ${RED}${BOLD}Some checks failed ✗${NC}"
  echo ""
  echo -e "  ${YELLOW}Troubleshooting:${NC}"
  echo -e "  → Check Lambda logs: aws logs tail /aws/lambda/autoops-api-dev --follow"
  echo -e "  → Run terraform plan to check for drift"
  echo -e "  → Read docs/06-troubleshooting.md"
fi
echo -e "${BOLD}══════════════════════════════════════${NC}"
echo ""
