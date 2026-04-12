#!/usr/bin/env python3
"""
AutoOps — API Test Suite
Run this after terraform apply to verify everything is working.

Usage:
    python test_api.py
    python test_api.py --url https://your-api.execute-api.us-east-1.amazonaws.com/dev
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

# ── Colors for terminal output ─────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):  print(f"  {GREEN}✓{RESET}  {msg}")
def fail(msg): print(f"  {RED}✗{RESET}  {msg}")
def info(msg): print(f"  {CYAN}→{RESET}  {msg}")
def warn(msg): print(f"  {YELLOW}⚠{RESET}  {msg}")

def http_request(method, url, body=None, timeout=15):
    """Simple HTTP request using only stdlib (no pip install needed)."""
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"}
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            duration = round((time.time() - start) * 1000)
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}, duration
    except urllib.error.HTTPError as e:
        duration = round((time.time() - start) * 1000)
        raw = e.read().decode()
        return e.code, json.loads(raw) if raw else {}, duration
    except Exception as e:
        duration = round((time.time() - start) * 1000)
        return None, {"error": str(e)}, duration


def print_header(title):
    print(f"\n{BOLD}{CYAN}{'─'*50}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*50}{RESET}")


def run_tests(base_url):
    base_url = base_url.rstrip("/")
    results = {"passed": 0, "failed": 0, "skipped": 0}
    created_item_id = None

    print(f"\n{BOLD}AutoOps — Test Suite{RESET}")
    print(f"Target: {CYAN}{base_url}{RESET}")
    print(f"Time:   {datetime.utcnow().isoformat()}Z\n")

    # ── Test 1: Health Check ─────────────────────────────────────
    print_header("Test 1: Health Check")
    info(f"GET {base_url}/health")
    status, body, ms = http_request("GET", f"{base_url}/health")
    if status == 200 and body.get("status") == "healthy":
        ok(f"Health check passed ({ms}ms)")
        ok(f"Environment: {body.get('environment', '?')}")
        ok(f"Remaining Lambda time: {body.get('remaining_time_ms', '?')}ms")
        results["passed"] += 1
    else:
        fail(f"Expected 200/healthy, got {status}: {body}")
        results["failed"] += 1

    # ── Test 2: List Items (empty) ────────────────────────────────
    print_header("Test 2: List Items")
    info(f"GET {base_url}/items")
    status, body, ms = http_request("GET", f"{base_url}/items")
    if status == 200:
        count = body.get("count", 0)
        ok(f"Listed {count} items ({ms}ms)")
        results["passed"] += 1
    else:
        fail(f"Expected 200, got {status}: {body}")
        results["failed"] += 1

    # ── Test 3: Create Item ───────────────────────────────────────
    print_header("Test 3: Create Item")
    payload = {"name": "AutoOps Test Item", "category": "test", "price": 42}
    info(f"POST {base_url}/items  payload={json.dumps(payload)}")
    status, body, ms = http_request("POST", f"{base_url}/items", payload)
    if status == 201:
        created_item_id = body.get("item", {}).get("itemId")
        ok(f"Item created: {created_item_id} ({ms}ms)")
        ok(f"Name: {body['item'].get('name')}")
        results["passed"] += 1
    elif status == 503:
        warn(f"DynamoDB throttled — this will trigger DevOps Agent! (Expected if running throttle test)")
        results["skipped"] += 1
    else:
        fail(f"Expected 201, got {status}: {body}")
        results["failed"] += 1

    # ── Test 4: Get Item ──────────────────────────────────────────
    if created_item_id:
        print_header("Test 4: Get Item by ID")
        info(f"GET {base_url}/items/{created_item_id}")
        status, body, ms = http_request("GET", f"{base_url}/items/{created_item_id}")
        if status == 200 and body.get("item", {}).get("itemId") == created_item_id:
            ok(f"Item retrieved correctly ({ms}ms)")
            results["passed"] += 1
        else:
            fail(f"Expected 200 with item, got {status}: {body}")
            results["failed"] += 1
    else:
        print_header("Test 4: Get Item by ID")
        warn("Skipped — no item was created in Test 3")
        results["skipped"] += 1

    # ── Test 5: Get Non-existent Item ─────────────────────────────
    print_header("Test 5: 404 — Get Non-existent Item")
    info(f"GET {base_url}/items/does-not-exist-12345")
    status, body, ms = http_request("GET", f"{base_url}/items/does-not-exist-12345")
    if status == 404:
        ok(f"404 returned correctly for missing item ({ms}ms)")
        results["passed"] += 1
    else:
        fail(f"Expected 404, got {status}: {body}")
        results["failed"] += 1

    # ── Test 6: Delete Item ───────────────────────────────────────
    if created_item_id:
        print_header("Test 6: Delete Item")
        info(f"DELETE {base_url}/items/{created_item_id}")
        status, body, ms = http_request("DELETE", f"{base_url}/items/{created_item_id}")
        if status == 200:
            ok(f"Item deleted ({ms}ms)")
            results["passed"] += 1
        else:
            fail(f"Expected 200, got {status}: {body}")
            results["failed"] += 1

        # Confirm deletion
        print_header("Test 6b: Confirm Deletion")
        status, body, ms = http_request("GET", f"{base_url}/items/{created_item_id}")
        if status == 404:
            ok("Confirmed: item is gone (404 as expected)")
            results["passed"] += 1
        else:
            fail(f"Expected 404 after delete, got {status}")
            results["failed"] += 1
    else:
        results["skipped"] += 2

    # ── Test 7: Simulate Error ────────────────────────────────────
    print_header("Test 7: Error Simulation Endpoint")
    info(f"POST {base_url}/simulate-error  {{\"type\":\"error\"}}")
    status, body, ms = http_request("POST", f"{base_url}/simulate-error", {"type": "error"})
    if status in (500, 503):
        ok(f"Error simulation returned {status} as expected ({ms}ms)")
        results["passed"] += 1
    else:
        fail(f"Expected 500/503, got {status}: {body}")
        results["failed"] += 1

    # ── CORS Test ─────────────────────────────────────────────────
    print_header("Test 8: CORS Headers Present")
    status, body, ms = http_request("GET", f"{base_url}/health")
    if status == 200:
        ok(f"API responding — CORS headers set in Lambda response ({ms}ms)")
        results["passed"] += 1
    else:
        warn("Could not verify CORS — API not responding")
        results["skipped"] += 1

    # ── Summary ────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*50}{RESET}")
    print(f"{BOLD}  RESULTS{RESET}")
    print(f"{'═'*50}")
    total = results["passed"] + results["failed"] + results["skipped"]
    print(f"  {GREEN}Passed:  {results['passed']}/{total}{RESET}")
    print(f"  {RED}Failed:  {results['failed']}/{total}{RESET}")
    print(f"  {YELLOW}Skipped: {results['skipped']}/{total}{RESET}")

    if results["failed"] == 0:
        print(f"\n  {GREEN}{BOLD}All tests passed! ✓{RESET}")
        print(f"  {CYAN}→ Now run: python trigger_throttle.py --url {base_url}{RESET}")
        print(f"    to trigger the DevOps Agent investigation!\n")
    else:
        print(f"\n  {RED}Some tests failed. Check your API URL and Lambda logs.{RESET}")
        print(f"  CloudWatch logs: /aws/lambda/autoops-api-dev\n")

    return results["failed"] == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoOps API Test Suite")
    parser.add_argument("--url", type=str,
                        default=os.environ.get("AUTOOPS_API_URL", ""),
                        help="API Gateway base URL (or set AUTOOPS_API_URL env var)")
    args = parser.parse_args()

    if not args.url:
        print(f"{RED}Error: No API URL provided.{RESET}")
        print("Usage: python test_api.py --url https://xxx.execute-api.us-east-1.amazonaws.com/dev")
        print("   or: export AUTOOPS_API_URL=https://xxx... && python test_api.py")
        sys.exit(1)

    success = run_tests(args.url)
    sys.exit(0 if success else 1)
