# Step 4 — AWS DevOps Agent Setup

This is where you connect the AWS DevOps Agent to your infrastructure.
The Agent is a managed AWS service — you configure it through the console, not code.

Estimated time: 15 minutes

---

## Before You Start

Make sure you have completed:
- ✅ Step 2 (Terraform deploy) — your infrastructure is running
- ✅ Step 3 (Slack setup) — Slack is connected
- ✅ You have your `terraform output` values saved somewhere

You will need these values from your terraform output:
- `devops_agent_role_arn` — looks like `arn:aws:iam::123456789:role/autoops-devops-agent-role-dev`
- `lambda_function_name` — looks like `autoops-api-dev`
- `dynamodb_table_name` — looks like `autoops-items-dev`

---

## IMPORTANT — AWS Support Plan Requirement

AWS DevOps Agent requires a paid AWS Support plan.

| Support Plan | Minimum Cost | DevOps Agent |
|---|---|---|
| Basic (free) | $0/month | ❌ Not eligible |
| Developer | $29/month | ❌ Not eligible |
| Business | ~$100/month | ✅ Eligible (30% credit) |
| Enterprise On-Ramp | $5,500/month | ✅ Eligible (75% credit) |

**If you are on Basic or Developer support:**
- You cannot use the DevOps Agent console
- All your infrastructure (Lambda, DynamoDB, alarms) still works
- CloudWatch alarms still fire and email you when problems occur
- The Slack notifications via AWS Chatbot still work
- You just won't have the automatic AI root-cause analysis from DevOps Agent
- Everything in Steps 5 and 6 still works

**To upgrade to Business Support:**
1. Go to AWS Console → click your account name (top right)
2. Select "Support Center"
3. Click "Change plan" under your current plan
4. Select "Business" and follow the prompts
5. Takes effect immediately

---

## PART 1 — Open AWS DevOps Agent Console

1. Log into AWS Console at https://console.aws.amazon.com
2. In the search bar at the top, type: `DevOps Agent`
3. Click "AWS DevOps Agent" from the results
   (If you don't see it, make sure you have Business Support or higher)
4. You're now on the DevOps Agent home page

---

## PART 2 — Create an Agent Space

An "Agent Space" is like a project folder inside DevOps Agent.
It groups all your resources together so the Agent knows what to monitor.

### Step 2.1 — Start Creation

1. Click "Create Agent Space" button
2. A wizard opens with multiple steps

---

### Step 2.2 — Basic Configuration

**Agent Space name:**
Type: `autoops-incident-intelligence`

**Description:**
Type: `Monitors the AutoOps serverless API for incidents`

**Tags (optional):**
- Key: `Project`, Value: `AutoOps`
- Key: `Environment`, Value: `dev`

Click "Next"

---

### Step 2.3 — IAM Role Configuration

This is where you paste the role ARN that Terraform created.

1. Under "IAM role", select "Use an existing IAM role"
2. In the Role ARN field, paste your `devops_agent_role_arn` from terraform output
   It looks like: `arn:aws:iam::123456789012:role/autoops-devops-agent-role-dev`
3. Click "Verify role" — it should show a green checkmark
4. Click "Next"

**Why this role matters:**
This role allows DevOps Agent to read your CloudWatch metrics, Lambda logs,
DynamoDB metrics, and X-Ray traces. Without it, the Agent is blind.
Terraform already created this role with exactly the right permissions.

---

### Step 2.4 — Connect Data Sources

This tells the Agent WHERE to look when something goes wrong.

**CloudWatch Logs:**
1. Click "Add log group"
2. Search for `/aws/lambda/autoops-api-dev`
3. Select it and click "Add"
4. Click "Add log group" again
5. Search for `/aws/apigateway/autoops-dev`
6. Select it and click "Add"

**CloudWatch Alarms:**
1. Click "Add alarms"
2. In the search box, type `autoops`
3. You'll see 6 alarms listed — select ALL of them:
   - `autoops-lambda-errors-dev`
   - `autoops-lambda-high-duration-dev`
   - `autoops-lambda-throttles-dev`
   - `autoops-dynamodb-write-throttles-dev`
   - `autoops-dynamodb-read-throttles-dev`
   - `autoops-api-5xx-errors-dev`
4. Click "Add"

**X-Ray (Distributed Tracing):**
1. Under "X-Ray groups", click "Add X-Ray group"
2. Select "Default" group
3. This gives the Agent access to trace data from Lambda

Click "Next"

---

### Step 2.5 — Connect AWS Resources

This tells the Agent WHICH specific services are part of your application.

**Lambda Functions:**
1. Click "Add resource"
2. Select "AWS Lambda" from the dropdown
3. Search for `autoops-api-dev`
4. Select it and click "Add"

**DynamoDB Tables:**
1. Click "Add resource"
2. Select "Amazon DynamoDB" from the dropdown
3. Search for `autoops-items-dev`
4. Select it and click "Add"

**API Gateway:**
1. Click "Add resource"
2. Select "Amazon API Gateway" from the dropdown
3. Search for `autoops-api-dev`
4. Select it and click "Add"

Click "Next"

---

### Step 2.6 — Notification Settings (Slack Integration)

This is how DevOps Agent sends its analysis to your Slack.

1. Under "Notification channel", select "Slack"
2. Select your workspace from the dropdown
   (you should see "AutoOps Monitoring" or whatever you named it)
3. Select the channel `#aws-incidents`
4. Under "Notification preferences":
   - Check "Investigation started"
   - Check "Investigation complete"
   - Check "Remediation recommendations"
5. Click "Next"

---

### Step 2.7 — Generate Generic Webhook (REQUIRED for Alarm Integration)

**IMPORTANT:** DevOps Agent does NOT automatically receive CloudWatch alarm notifications through SNS. Instead, you must configure a webhook that receives alarm events via EventBridge → Lambda.

1. After creating the Agent Space, go to the "Capabilities" tab
2. Scroll to "Generic Webhook" section
3. Click "Generate webhook"
4. Copy the webhook URL (looks like: `https://event-ai.us-east-1.api.aws/webhook/generic/YOUR_WEBHOOK_ID`)
5. Copy the webhook key and secret (you'll need these for authentication)

**Store Webhook Credentials in AWS Secrets Manager:**

Run this command in your terminal (replace the placeholders):

```bash
aws secretsmanager create-secret \
  --name /autoops/dev/devops-agent-webhook \
  --secret-string '{"url":"YOUR_WEBHOOK_URL","key":"YOUR_KEY","secret":"YOUR_SECRET"}' \
  --region us-east-1
```

**Update Terraform Configuration:**

1. Open `terraform/terraform.tfvars`
2. Set `enable_devops_agent_integration = true`
3. Set `devops_agent_webhook_secret_arn` to the ARN from the command output
4. Run `terraform apply` to deploy the EventBridge rule and Lambda function

**Architecture:**
```
CloudWatch Alarm → EventBridge (automatic) → Lambda Function → DevOps Agent Webhook
```

The Lambda function:
- Retrieves webhook credentials from Secrets Manager
- Formats alarm data for DevOps Agent
- Calculates HMAC SHA-256 signature for authentication
- POSTs to the webhook endpoint with retries

---

### Step 2.8 — Review and Create

1. Review all the settings you've entered
2. Verify the IAM role ARN looks correct
3. Verify the 6 alarms are all listed
4. Verify Lambda, DynamoDB, and API Gateway are listed as resources
5. Verify Slack channel is configured
6. Click "Create Agent Space"

You'll see: "Agent Space created successfully"

**IMPORTANT:** After creating the Agent Space, complete Step 2.7 to generate the webhook and configure the EventBridge integration. Without this, the DevOps Agent will NOT receive alarm notifications.

---

## PART 3 — Verify DevOps Agent is Active

### Step 3.1 — Check Status

1. In the DevOps Agent console, click on your Agent Space
2. You should see status: "Active" with a green indicator
3. Under "Connected resources", you should see all 3 resources
4. Under "Monitoring", you should see "6 alarms connected"

If anything shows as "Not connected" or "Error":
- Check your IAM role ARN was entered correctly
- Verify the role was created by running: `terraform output devops_agent_role_arn`

---

### Step 3.2 — Send a Test Alarm

Let's verify DevOps Agent receives alarms correctly:

1. In AWS Console, go to CloudWatch → Alarms
2. Find `autoops-lambda-errors-dev`
3. Click on it, then click "Actions" → "Temporarily set to ALARM state"
4. Add a note: "Testing DevOps Agent connection"
5. Click "Set to ALARM"
6. Wait 2-3 minutes
7. Check your Slack #aws-incidents channel

If you see an investigation message in Slack: **Everything is working!**

To clear the alarm:
1. Go back to CloudWatch → Alarms
2. Click on the alarm
3. Click "Actions" → "Reset to OK"

---

## PART 4 — Understanding What DevOps Agent Does

When your DynamoDB throttles (from the test in Step 5), here is exactly
what DevOps Agent does automatically — step by step:

```
Second 0:    CloudWatch alarm fires: "WriteThrottleEvents ≥ 1"
             → Alarm publishes to SNS topic (email + Slack via Chatbot)
             → Alarm event automatically sent to EventBridge
Second 2:    EventBridge rule matches alarm state change (ALARM state)
             → Triggers Lambda function
Second 3:    Lambda function executes:
             → Retrieves webhook credentials from Secrets Manager
             → Formats alarm data for DevOps Agent
             → Calculates HMAC signature
             → POSTs to DevOps Agent webhook
Second 5:    DevOps Agent receives webhook notification
             → Detects alarm state change
Second 10:   Agent begins topology discovery:
             → Identifies Lambda function as connected to DynamoDB
             → Identifies API Gateway as connected to Lambda
Second 30:   Agent queries CloudWatch Logs:
             → Finds Lambda error logs with "ProvisionedThroughputExceededException"
             → Correlates timing with alarm trigger
Minute 1:    Agent queries X-Ray traces:
             → Finds traces with DynamoDB write failures
             → Identifies which API route caused the throttle (/items POST)
Minute 2:    Agent queries DynamoDB metrics:
             → Confirms: 1 WCU provisioned, 47 WCU consumed in burst
             → Identifies this as capacity mismatch
Minute 3:    Agent generates natural-language root cause report
Minute 4:    Agent posts full analysis to Slack #aws-incidents
```

Total: ~4 minutes from alarm to Slack diagnosis — zero human involvement.

**Architecture Flow:**
```
CloudWatch Alarm → EventBridge (automatic) → Lambda → DevOps Agent Webhook → Investigation → Slack
                ↓
              SNS Topic → Email + Slack (Chatbot) [preserved]
```

---

## Summary — Your DevOps Agent Setup

After completing this step, your stack looks like this:

```
Your App (Lambda + DynamoDB + API Gateway)
    │
    ├── CloudWatch alarms watching for problems
    │   │
    │   ├── SNS Topic → Email notifications (preserved)
    │   │            → Slack via AWS Chatbot (preserved)
    │   │
    │   └── EventBridge (automatic) → Lambda Function → DevOps Agent Webhook
    │
    └── AWS DevOps Agent Space
            │
            ├── Connected to: Lambda logs
            ├── Connected to: DynamoDB metrics
            ├── Connected to: API Gateway logs
            ├── Connected to: X-Ray traces
            ├── Receives: Alarm notifications via webhook
            │
            └── Sends findings to: Slack #aws-incidents
```

**Key Points:**
- Email and Slack (Chatbot) notifications continue to work unchanged
- DevOps Agent receives alarm notifications via EventBridge → Lambda → Webhook
- The webhook integration is deployed automatically by Terraform when enabled
- All notification channels work in parallel (email, Slack, DevOps Agent)

---

→ Next: `docs/05-testing-guide.md`
