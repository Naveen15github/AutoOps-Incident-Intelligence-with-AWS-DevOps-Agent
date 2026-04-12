#!/usr/bin/env python3
"""
AutoOps — Throttle Storm Trigger
THIS IS THE MAIN DEMO SCRIPT.

It fires 50 rapid write requests at your DynamoDB,
intentionally causing WriteThrottleEvents.

What happens next:
  1. DynamoDB throttles the writes (1 WCU can't handle 50 burst requests)
  2. CloudWatch alarm "autoops-dynamodb-write-throttles-dev" fires
  3. AWS DevOps Agent detects the alarm
  4. Agent fetches Lambda logs, DynamoDB metrics, X-Ray traces
  5. Agent posts root-cause analysis to your Slack channel
  6. You see "DynamoDB WCU exhausted — recommend On-Demand mode" in Slack

Usage:
    python trigger_throttle.py --url https://your-api.execute-api.us-east-1.amazonaws.com/dev
    python trigger_throttle.py --url <URL> --count 100  # more aggressive
"""

import argparse
import json
import os
import sys
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

results_lock = threading.Lock()
results = {"success": 0, "throttled": 0, "error": 0, "total": 0}


def send_request(base_url, index):
    """Fire a single write request to DynamoDB via Lambda."""
    payload = json.dumps({
        "name": f"ThrottleTest-{index}-{int(time.time())}",
        "category": "throttle-test",
        "price": index
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/items",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception:
        status = 0

    with results_lock:
        results["total"] += 1
        if status == 201:
            results["success"] += 1
        elif status == 503:
            results["throttled"] += 1
        else:
            results["error"] += 1


def run_throttle_storm(base_url, count=50, wave_size=10, wave_delay=0.1):
    """Fire `count` requests in rapid waves to trigger throttling."""
    base_url = base_url.rstrip("/")

    print(f"\n{BOLD}{RED}{'═'*55}{RESET}")
    print(f"{BOLD}{RED}  🔴 THROTTLE STORM INITIATING{RESET}")
    print(f"{BOLD}{RED}{'═'*55}{RESET}")
    print(f"\n  Target:    {CYAN}{base_url}{RESET}")
    print(f"  Requests:  {YELLOW}{count} burst writes{RESET}")
    print(f"  Goal:      Trip DynamoDB WriteThrottleEvents alarm")
    print(f"  Expected:  DevOps Agent investigation in ~2-5 minutes")
    print(f"\n  {YELLOW}Starting in 3 seconds... Ctrl+C to abort{RESET}")
    time.sleep(3)

    print(f"\n  {RED}FIRING...{RESET}\n")
    start_time = time.time()
    threads = []

    for i in range(count):
        t = threading.Thread(target=send_request, args=(base_url, i))
        threads.append(t)
        t.start()

        # Brief pause between waves to let progress show
        if (i + 1) % wave_size == 0:
            completed = results["total"]
            print(f"  Wave {(i+1)//wave_size:2d} complete — "
                  f"{GREEN}{results['success']} ok{RESET}  "
                  f"{RED}{results['throttled']} throttled{RESET}  "
                  f"{YELLOW}{results['error']} error{RESET}  "
                  f"({completed}/{count})")
            time.sleep(wave_delay)

    # Wait for all threads
    for t in threads:
        t.join(timeout=15)

    elapsed = round(time.time() - start_time, 1)

    print(f"\n{'─'*55}")
    print(f"\n  {BOLD}STORM COMPLETE{RESET}  ({elapsed}s)\n")
    print(f"  {GREEN}✓ Succeeded:  {results['success']}{RESET}")
    print(f"  {RED}✗ Throttled:  {results['throttled']}{RESET}")
    print(f"  {YELLOW}⚠ Other err:  {results['error']}{RESET}")

    throttle_pct = round(results["throttled"] / count * 100)
    print(f"\n  Throttle rate: {BOLD}{throttle_pct}%{RESET}")

    print(f"\n{'═'*55}")

    if results["throttled"] > 0:
        print(f"\n  {GREEN}{BOLD}✓ THROTTLE EVENTS GENERATED!{RESET}")
        print(f"\n  What happens now:")
        print(f"  {CYAN}1.{RESET} CloudWatch 'WriteThrottleEvents' alarm is firing")
        print(f"  {CYAN}2.{RESET} SNS notification sent to your email")
        print(f"  {CYAN}3.{RESET} AWS DevOps Agent detected the alarm")
        print(f"  {CYAN}4.{RESET} Agent is now correlating Lambda logs + X-Ray + DynamoDB")
        print(f"  {CYAN}5.{RESET} Root-cause report will arrive in Slack in ~2-5 minutes")
        print(f"\n  {YELLOW}→ Check your Slack #{'{autoops-incidents}'} channel!{RESET}")
        print(f"  {YELLOW}→ Check your email for SNS alarm notification{RESET}")
        print(f"  {YELLOW}→ Check CloudWatch dashboard for spike in metrics{RESET}")
    else:
        print(f"\n  {YELLOW}⚠ No throttle events — DynamoDB handled all {count} requests{RESET}")
        print(f"  This means your write capacity is sufficient for this burst.")
        print(f"  Try increasing --count or reducing --wave-delay:")
        print(f"    python trigger_throttle.py --url {base_url} --count 200 --wave-delay 0")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoOps Throttle Storm — triggers DevOps Agent")
    parser.add_argument("--url", type=str,
                        default=os.environ.get("AUTOOPS_API_URL", ""),
                        help="API Gateway base URL")
    parser.add_argument("--count", type=int, default=50,
                        help="Number of write requests to fire (default: 50)")
    parser.add_argument("--wave-size", type=int, default=10,
                        help="Requests per wave (default: 10)")
    parser.add_argument("--wave-delay", type=float, default=0.05,
                        help="Delay between waves in seconds (default: 0.05)")
    args = parser.parse_args()

    if not args.url:
        print(f"{RED}Error: No API URL provided.{RESET}")
        print("Usage: python trigger_throttle.py --url https://xxx.execute-api.us-east-1.amazonaws.com/dev")
        sys.exit(1)

    run_throttle_storm(args.url, args.count, args.wave_size, args.wave_delay)
