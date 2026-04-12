# Tests — README

This folder has 3 test files. Run them in this order.

## Requirements

- Python 3.x installed
- Your API URL from `terraform output api_endpoint`
- No extra packages needed — uses Python standard library only

## Set Your API URL (saves typing)

**Mac/Linux:**
```bash
export AUTOOPS_API_URL="https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev"
```

**Windows:**
```
set AUTOOPS_API_URL=https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev
```

After setting this, all tests pick it up automatically without `--url`.

---

## File 1: health_check.sh — Quick Check (30 seconds)

```bash
# Mac/Linux
chmod +x health_check.sh
./health_check.sh

# Or with explicit URL
./health_check.sh https://YOUR_API_URL
```

Checks: health endpoint, list items, create item, 404 handling, response time.

---

## File 2: test_api.py — Full Test Suite (2 minutes)

```bash
python test_api.py
# or
python test_api.py --url https://YOUR_API_URL
```

Tests: all CRUD operations, error handling, 404s, status codes.
Run this after every `terraform apply` to verify everything is still working.

---

## File 3: trigger_throttle.py — DevOps Agent Demo (5 minutes)

```bash
python trigger_throttle.py
# or
python trigger_throttle.py --url https://YOUR_API_URL --count 50
```

**This is the main demo script.**
Fires 50 rapid writes → trips DynamoDB alarm → AWS DevOps Agent investigates → Slack message.

Options:
```
--count N        Number of requests (default: 50)
--wave-size N    Requests per wave (default: 10)
--wave-delay S   Seconds between waves (default: 0.05)
```

After running, watch your Slack #aws-incidents channel for the Agent's analysis.
