# Step 5 — Testing Guide

This is where it all comes together.
Follow these tests in order — from basic verification to the full DevOps Agent demo.

---

## Before You Start

Have your API URL ready — from `terraform output api_endpoint`
It looks like: `https://abc123.execute-api.us-east-1.amazonaws.com/dev`

---

## TEST 1 — Quick Health Check (30 seconds)

Confirms your API is alive.

**Mac/Linux:**
```bash
cd tests
chmod +x health_check.sh
./health_check.sh https://YOUR_API_URL
```

**Windows:**
```
cd tests
python test_api.py --url https://YOUR_API_URL
```

**Expected result:**
```
✓  Health endpoint returned 200
✓  Items list returned 200
✓  Create item returned 201
✓  Unknown route correctly returned 404
✓  Stack is healthy ✓
```

If this passes, your Lambda + DynamoDB + API Gateway are all working correctly.

---

## TEST 2 — Full API Test Suite (2 minutes)

Tests every endpoint thoroughly.

```bash
cd tests
python test_api.py --url https://YOUR_API_URL
```

**Expected result:**
```
  ──────────────────────────────────────────────────
  Test 1: Health Check
  → GET https://...
  ✓  Health check passed (234ms)
  ✓  Environment: dev

  Test 2: List Items
  ✓  Listed 0 items (189ms)

  Test 3: Create Item
  ✓  Item created: a1b2c3d4-... (312ms)

  Test 4: Get Item by ID
  ✓  Item retrieved correctly (201ms)

  Test 5: 404 — Get Non-existent Item
  ✓  404 returned correctly (145ms)

  Test 6: Delete Item
  ✓  Item deleted (198ms)
  ✓  Confirmed: item is gone (404 as expected)

  Test 7: Error Simulation
  ✓  Error simulation returned 500 as expected (156ms)

  ══════════════════════════════════════════════════
  RESULTS
  ══════════════════════════════════════════════════
  Passed:  9/9
  Failed:  0/9
  Skipped: 0/9

  All tests passed! ✓
  → Now run: python trigger_throttle.py --url ...
```

---

## TEST 3 — Open the Live Dashboard (2 minutes)

1. Find the `website/index.html` file in your project folder
2. Double-click it to open in your browser
   (Or drag it into Chrome/Firefox)
3. At the top, paste your API URL and click "CONNECT"
4. Click the buttons in the Test Console to see live requests

You'll see:
- API status turning green (✓ OK)
- Request log filling up with each test
- Response times displayed
- Item count from DynamoDB updating

---

## TEST 4 — THE MAIN DEMO: Trigger DevOps Agent Investigation

This is the most important test.
It triggers a real CloudWatch alarm and demonstrates DevOps Agent investigation.

### What to prepare before running:
- [ ] Slack #aws-incidents channel is open and visible
- [ ] AWS CloudWatch console is open in another tab
- [ ] Your email inbox is open

### Run the throttle storm:

```bash
cd tests
python trigger_throttle.py --url https://YOUR_API_URL
```

**What you'll see in the terminal:**
```
═══════════════════════════════════════════════════════
  🔴 THROTTLE STORM INITIATING
═══════════════════════════════════════════════════════

  Target:    https://...
  Requests:  50 burst writes
  Goal:      Trip DynamoDB WriteThrottleEvents alarm
  Expected:  DevOps Agent investigation in ~2-5 minutes

  Starting in 3 seconds... Ctrl+C to abort

  FIRING...

  Wave  1 complete — 2 ok  8 throttled  0 error  (10/50)
  Wave  2 complete — 1 ok  9 throttled  0 error  (20/50)
  Wave  3 complete — 1 ok  9 throttled  0 error  (30/50)
  Wave  4 complete — 0 ok  10 throttled 0 error  (40/50)
  Wave  5 complete — 1 ok  9 throttled  0 error  (50/50)

  ─────────────────────────────────────────────────────

  STORM COMPLETE  (4.3s)

  ✓ Succeeded:  5
  ✗ Throttled:  45
  ⚠ Other err:  0

  Throttle rate: 90%

  ✓ THROTTLE EVENTS GENERATED!

  What happens now:
  1. CloudWatch 'WriteThrottleEvents' alarm is firing
  2. SNS notification sent to your email
  3. AWS DevOps Agent detected the alarm
  4. Agent is now correlating Lambda logs + X-Ray + DynamoDB
  5. Root-cause report will arrive in Slack in ~2-5 minutes

  → Check your Slack #aws-incidents channel!
  → Check your email for SNS alarm notification
  → Check CloudWatch dashboard for spike in metrics
```

### What to watch for:

**In CloudWatch (immediate):**
1. Go to CloudWatch → Alarms
2. Find `autoops-dynamodb-write-throttles-dev`
3. It should turn RED (In ALARM) within 1 minute

**In your email (1-2 minutes):**
```
Subject: ALARM: "autoops-dynamodb-write-throttles-dev" in US East (N. Virginia)

Alarm Details:
  Name:             autoops-dynamodb-write-throttles-dev
  Description:      DynamoDB write requests are being throttled
  State Change:     OK -> ALARM
  Reason:           Threshold Crossed: 45 write throttle events
```

**In Slack #aws-incidents (2-5 minutes):**

First message (alarm notification):
```
🚨 AWS CloudWatch Alarm
autoops-dynamodb-write-throttles-dev
State: ALARM
```

Second message (DevOps Agent analysis):
```
🤖 AWS DevOps Agent — Investigation Complete

Incident: DynamoDB Write Throttling
Affected: autoops-items-dev (DynamoDB) → autoops-api-dev (Lambda)

Root Cause:
The DynamoDB table 'autoops-items-dev' has provisioned write 
capacity of 1 WCU. During the incident window, write requests 
peaked at 45+ WCU, causing 90% of write requests to fail with 
ProvisionedThroughputExceededException.

Lambda logs confirm: 45 invocations returned HTTP 503.
X-Ray traces show: Average write latency 0ms (immediate rejection).

Recommendation:
Option 1 (Immediate): Switch DynamoDB billing to On-Demand mode
Option 2 (Cost-efficient): Increase provisioned WCU to 10-20

Confidence: HIGH
```

---

## TEST 5 — Verify CloudWatch Dashboard

1. Get your dashboard URL from terraform:
   ```
   terraform output cloudwatch_dashboard_url
   ```
2. Open that URL in your browser
3. You'll see 4 metric graphs:
   - Lambda errors and throttles (should show spikes)
   - DynamoDB throttle events (should show the 45-event spike)
   - Lambda P99 duration with anomaly band
   - API Gateway request count and 5XX errors

This visual confirms exactly what the DevOps Agent analyzed.

---

## TEST 6 — X-Ray Trace Analysis

1. Go to AWS Console → X-Ray → Traces
2. Set the time range to "Last 15 minutes"
3. You'll see the failed traces from the throttle storm
4. Click on any failed trace
5. You'll see the full call graph: API Gateway → Lambda → DynamoDB
6. Failed DynamoDB write calls show in red

This is the exact data DevOps Agent used to diagnose the problem.

---

## Optional: Run Custom Stress Test

If you want to explore more scenarios:

```bash
# More aggressive throttle (200 requests, no delay)
python trigger_throttle.py --url https://YOUR_API_URL --count 200 --wave-delay 0

# Gentler test (20 requests, slow waves)
python trigger_throttle.py --url https://YOUR_API_URL --count 20 --wave-size 5

# Simulate a 500 error
curl -X POST https://YOUR_API_URL/simulate-error \
  -H "Content-Type: application/json" \
  -d '{"type":"crash"}'
```

---

## What Each Test Proves

| Test | What It Demonstrates |
|---|---|
| Test 1 | Your serverless stack is deployed and healthy |
| Test 2 | All API endpoints work correctly |
| Test 3 | Live dashboard connects to your real API |
| Test 4 | DevOps Agent detects and diagnoses real incidents |
| Test 5 | CloudWatch collected all the metrics |
| Test 6 | X-Ray captured all the distributed traces |

---

→ If you hit any issues: `docs/06-troubleshooting.md`
