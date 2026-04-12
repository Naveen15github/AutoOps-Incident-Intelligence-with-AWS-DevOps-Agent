# AWS DevOps Agent Notification Endpoint Research

**Task:** 3.1 Research DevOps Agent notification endpoint  
**Date:** 2026  
**Context:** Investigating how to connect CloudWatch alarms to AWS DevOps Agent for automatic incident investigation

---

## Executive Summary

AWS DevOps Agent **does NOT have a direct SNS subscription endpoint**. The service uses alternative integration methods:

1. **EventBridge Integration** (Recommended) - CloudWatch alarms automatically emit events to EventBridge, which can trigger DevOps Agent investigations via webhooks
2. **Webhook Integration** - DevOps Agent provides webhook endpoints that can be called by external systems
3. **Manual Console "Connection"** - The console allows "connecting alarms" but this only grants read permissions, NOT push notifications

**Key Finding:** The original hypothesis that DevOps Agent has an SNS subscription endpoint is **incorrect**. The service architecture uses EventBridge and webhooks instead.

---

## Research Findings

### 1. CloudWatch Alarms → EventBridge Integration

**Source:** [AWS CloudWatch EventBridge Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch-and-eventbridge.html)

CloudWatch automatically sends alarm state change events to Amazon EventBridge:
- Event source: `aws.cloudwatch`
- Event types: Alarm state changes (OK → ALARM, ALARM → OK, etc.)
- No configuration required - events are sent automatically
- CloudWatch guarantees delivery of alarm state change events to EventBridge

**Event Pattern Example:**
```json
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "alarmName": ["autoops-lambda-errors-dev"],
    "state": {
      "value": ["ALARM"]
    }
  }
}
```

### 2. DevOps Agent Webhook Integration

**Source:** [AWS DevOps Agent Webhook Documentation](https://docs.aws.amazon.com/devopsagent/latest/userguide/configuring-capabilities-for-aws-devops-agent-invoking-devops-agent-through-webhook.html)

DevOps Agent provides webhook endpoints that can receive HTTP POST requests to trigger investigations:

**Webhook Types:**
- **Generic webhooks** - Manually created, use HMAC authentication
- **Integration-specific webhooks** - Auto-generated for third-party integrations (Datadog, Splunk, etc.)
- **Grafana alert webhooks** - Specialized for Grafana alert notifications

**Webhook Endpoint Format:**
```
https://event-ai.{region}.api.aws/webhook/generic/{WEBHOOK_ID}
```

**Authentication Methods:**
- HMAC (SHA-256 signature) - for generic webhooks
- Bearer token - for integration-specific webhooks

**Request Format:**
```json
{
  "eventType": "incident",
  "incidentId": "incident-123",
  "action": "created",
  "priority": "HIGH",
  "title": "High CPU usage on production server",
  "description": "Detailed incident description",
  "timestamp": "2025-11-23T18:00:00Z",
  "service": "MyTestService",
  "data": {
    "metadata": {
      "region": "us-east-1",
      "environment": "production"
    }
  }
}
```

### 3. DevOps Agent Investigation Triggers

**Source:** [AWS DevOps Agent Autonomous Incident Response](https://docs.aws.amazon.com/devopsagent/latest/userguide/working-with-devops-agent-autonomous-incident-response.html)

DevOps Agent investigations can be started in three ways:

1. **Built-in integrations** - ServiceNow, PagerDuty (via webhooks)
2. **Webhooks** - Generic webhooks for custom integrations
3. **Manual** - Through the DevOps Agent web app console

**Important:** The documentation does NOT mention SNS as a trigger mechanism.

### 4. Console "Connect Alarms" Feature

**Source:** [DevOps Agent Setup Documentation](docs/04-devops-agent-setup.md)

The AWS Console allows "connecting alarms" to a DevOps Agent Space:
- This grants the Agent **read permissions** to query alarm state and history
- This does **NOT** create a push notification mechanism
- The Agent can query alarm data during investigations but won't be automatically notified when alarms fire

**From the setup documentation:**
> Under "Monitoring", you should see "6 alarms connected"

This connection is for **topology discovery** and **investigation context**, not for triggering investigations.

### 5. DevOps Agent EventBridge Events (Outbound Only)

**Source:** [AWS DevOps Agent EventBridge Integration](https://docs.aws.amazon.com/devopsagent/latest/userguide/configuring-capabilities-for-aws-devops-agent-integrating-devops-agent-into-event-driven-applications-using-amazon-eventbridge-index.html)

DevOps Agent **sends** events to EventBridge when investigation/mitigation states change:
- Event source: `aws.aidevops`
- Event types: Investigation Created, Investigation Completed, Investigation Failed, etc.
- This is **outbound only** - DevOps Agent publishes events, doesn't consume them

**This is NOT the mechanism for triggering investigations from CloudWatch alarms.**

---

## Recommended Solution Architecture

Based on the research, here is the recommended approach to connect CloudWatch alarms to DevOps Agent:

### Option 1: EventBridge → Lambda → DevOps Agent Webhook (Recommended)

```
CloudWatch Alarm fires
    ↓
EventBridge receives alarm state change event (automatic)
    ↓
EventBridge Rule matches alarm events
    ↓
Lambda function triggered
    ↓
Lambda formats alarm data and calls DevOps Agent webhook
    ↓
DevOps Agent starts investigation
```

**Advantages:**
- No SNS subscription needed
- Leverages existing EventBridge integration
- Can filter and transform alarm data before sending to DevOps Agent
- Can add custom logic (e.g., only trigger for specific alarms)

**Implementation Requirements:**
1. Create EventBridge rule to match CloudWatch alarm state changes
2. Create Lambda function to format alarm data and call DevOps Agent webhook
3. Generate DevOps Agent generic webhook in console
4. Store webhook URL and credentials in AWS Secrets Manager
5. Grant Lambda permission to read secrets and invoke webhook

### Option 2: SNS → Lambda → DevOps Agent Webhook

```
CloudWatch Alarm fires
    ↓
SNS topic receives notification (existing)
    ↓
Lambda function subscribed to SNS topic
    ↓
Lambda formats alarm data and calls DevOps Agent webhook
    ↓
DevOps Agent starts investigation
```

**Advantages:**
- Minimal changes to existing infrastructure
- Preserves existing SNS subscriptions (email, Chatbot)
- Can reuse existing SNS topic

**Implementation Requirements:**
1. Add Lambda function as SNS topic subscriber
2. Lambda formats SNS message and calls DevOps Agent webhook
3. Generate DevOps Agent generic webhook in console
4. Store webhook URL and credentials in AWS Secrets Manager

### Option 3: Manual Investigation Trigger (Current Workaround)

Users manually start investigations through the DevOps Agent web app when they receive Slack/email notifications.

**Disadvantages:**
- Not autonomous
- Defeats the purpose of DevOps Agent
- Adds manual overhead

---

## DevOps Agent Webhook Discovery Process

To obtain the webhook endpoint for DevOps Agent:

### Step 1: Access DevOps Agent Console
1. Navigate to AWS DevOps Agent console: https://console.aws.amazon.com/devops-agent
2. Select your Agent Space: `autoops-incident-intelligence`
3. Go to the **Capabilities** tab

### Step 2: Generate Generic Webhook
1. In the **Webhook** section, click **Configure**
2. Click **Generate webhook**
3. The system generates:
   - Webhook endpoint URL (format: `https://event-ai.us-east-1.api.aws/webhook/generic/{WEBHOOK_ID}`)
   - HMAC key pair (key and secret)
4. **CRITICAL:** Store the key and secret immediately - they cannot be retrieved later

### Step 3: Store Credentials Securely
Store webhook credentials in AWS Secrets Manager:
```bash
aws secretsmanager create-secret \
  --name /autoops/dev/devops-agent-webhook \
  --secret-string '{
    "url": "https://event-ai.us-east-1.api.aws/webhook/generic/YOUR_WEBHOOK_ID",
    "key": "YOUR_WEBHOOK_KEY",
    "secret": "YOUR_WEBHOOK_SECRET"
  }' \
  --region us-east-1
```

### Step 4: Test Webhook
Use the provided cURL example to test:
```bash
#!/bin/bash
WEBHOOK_URL="https://event-ai.us-east-1.api.aws/webhook/generic/YOUR_WEBHOOK_ID"
SECRET="YOUR_WEBHOOK_SECRET"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
INCIDENT_ID="test-alert-$(date +%s)"

PAYLOAD=$(cat <<EOF
{
  "eventType": "incident",
  "incidentId": "$INCIDENT_ID",
  "action": "created",
  "priority": "HIGH",
  "title": "Test CloudWatch Alarm",
  "description": "Testing DevOps Agent webhook integration",
  "service": "AutoOps",
  "timestamp": "$TIMESTAMP"
}
EOF
)

SIGNATURE=$(echo -n "${TIMESTAMP}:${PAYLOAD}" | openssl dgst -sha256 -hmac "$SECRET" -binary | base64)

curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "x-amzn-event-timestamp: $TIMESTAMP" \
  -H "x-amzn-event-signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

Expected response: HTTP 200 with message "webhook received"

---

## Implementation Recommendation

**Recommended Approach:** Option 1 (EventBridge → Lambda → DevOps Agent Webhook)

**Rationale:**
1. **Native AWS Integration:** CloudWatch alarms automatically emit events to EventBridge - no additional configuration needed
2. **Decoupled Architecture:** EventBridge provides a clean event-driven architecture
3. **Flexibility:** Can easily add filtering, transformation, or routing logic
4. **Preservation:** Existing SNS subscriptions (email, Chatbot) remain unchanged
5. **Scalability:** EventBridge handles high event volumes efficiently

**Next Steps:**
1. Generate DevOps Agent webhook in console (Task 3.2)
2. Create Lambda function to bridge EventBridge and DevOps Agent webhook (Task 3.3)
3. Create EventBridge rule to trigger Lambda on alarm state changes (Task 3.4)
4. Test end-to-end integration (Task 4.x)

---

## Alternative Approaches Considered and Rejected

### ❌ Direct SNS Subscription to DevOps Agent
**Why Rejected:** DevOps Agent does not expose an SNS-compatible endpoint. The service uses webhooks with HMAC/Bearer token authentication, which SNS does not support natively.

### ❌ SNS → HTTPS Subscription to Webhook
**Why Rejected:** SNS HTTPS subscriptions require subscription confirmation, which DevOps Agent webhooks don't support. Additionally, SNS doesn't support custom authentication headers (HMAC signature).

### ❌ Modify CloudWatch Alarms to Call Webhook Directly
**Why Rejected:** CloudWatch alarms don't support webhook actions. Supported actions are: SNS, EC2 actions, Auto Scaling, Systems Manager, Lambda (but only via SNS).

---

## References

1. [AWS DevOps Agent Webhook Documentation](https://docs.aws.amazon.com/devopsagent/latest/userguide/configuring-capabilities-for-aws-devops-agent-invoking-devops-agent-through-webhook.html)
2. [AWS DevOps Agent EventBridge Integration](https://docs.aws.amazon.com/devopsagent/latest/userguide/configuring-capabilities-for-aws-devops-agent-integrating-devops-agent-into-event-driven-applications-using-amazon-eventbridge-index.html)
3. [CloudWatch Alarm Events and EventBridge](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch-and-eventbridge.html)
4. [AWS DevOps Agent Autonomous Incident Response](https://docs.aws.amazon.com/devopsagent/latest/userguide/working-with-devops-agent-autonomous-incident-response.html)
5. [AWS DevOps Agent Blog Post](https://aws.amazon.com/blogs/aws/aws-devops-agent-helps-you-accelerate-incident-response-and-improve-system-reliability-preview/)

---

## Conclusion

The root cause hypothesis in the design document was partially correct:
- ✅ Correct: DevOps Agent is not receiving alarm notifications
- ✅ Correct: There is no subscription connecting alarms to DevOps Agent
- ❌ Incorrect: The solution is NOT an SNS subscription
- ✅ Correct: The endpoint format is service-managed and not exposed in Terraform

**The actual solution:** Use EventBridge (which already receives CloudWatch alarm events) to trigger a Lambda function that calls the DevOps Agent webhook endpoint.

This approach:
- Preserves all existing notification channels (email, Slack via Chatbot)
- Adds DevOps Agent investigation triggering
- Uses native AWS event-driven architecture
- Requires minimal infrastructure changes
