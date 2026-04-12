# DevOps Agent Webhook Integration Implementation

## Overview

This document describes the implementation of Task 3.3 from the bugfix spec: creating EventBridge rule and Lambda function for DevOps Agent webhook integration.

## Problem Statement

The original task was to "Update SNS topic policy to allow DevOps Agent subscription", but research in Task 3.1 revealed that AWS DevOps Agent does NOT use SNS subscriptions. Instead, it uses a webhook-based architecture.

## Solution Architecture

```
CloudWatch Alarm → EventBridge (automatic) → Lambda Function → DevOps Agent Webhook
                ↓
              SNS Topic → Email + Slack (Chatbot) [preserved]
```

### Key Components

1. **EventBridge Rule** (`terraform/eventbridge.tf`)
   - Automatically captures CloudWatch alarm state change events
   - Filters for ALARM state only (not OK or INSUFFICIENT_DATA)
   - Triggers Lambda function when alarm fires
   - Conditional creation: only created if `var.enable_devops_agent_integration == true`

2. **Lambda Function** (`terraform/lambda_devops_agent.tf`)
   - Runtime: Python 3.12
   - Purpose: Receive EventBridge events and call DevOps Agent webhook
   - Retrieves webhook credentials from AWS Secrets Manager
   - Formats alarm data for DevOps Agent webhook format
   - Calculates HMAC SHA-256 signature for authentication
   - POSTs to DevOps Agent webhook endpoint with retry logic
   - Conditional creation: only created if `var.enable_devops_agent_integration == true`

3. **Lambda Function Code** (`lambda_devops_agent/lambda_function.py`)
   - Extracts alarm details from EventBridge event
   - Retrieves webhook credentials (url, key, secret) from Secrets Manager
   - Formats payload in DevOps Agent webhook format
   - Calculates HMAC signature: `HMAC-SHA256(payload, secret)`
   - Sends POST request with authentication headers
   - Implements exponential backoff retry logic (max 3 attempts)
   - Handles errors and logs to CloudWatch Logs

4. **IAM Permissions** (`terraform/lambda_devops_agent.tf`)
   - Lambda execution role with basic execution permissions
   - Secrets Manager read permission for webhook credentials
   - CloudWatch Logs write permissions

## Preservation of Existing Functionality

**CRITICAL:** The implementation preserves all existing notification channels:

- **SNS Topic** (`terraform/sns.tf`): NO CHANGES
  - Email subscription continues to work
  - AWS Chatbot (Slack) subscription continues to work
  - CloudWatch publish permissions unchanged

- **CloudWatch Alarms**: NO CHANGES
  - All alarm configurations unchanged
  - SNS topic actions preserved
  - Alarm thresholds unchanged

## Configuration

### Terraform Variables

Two new variables were added in Task 3.2 (`terraform/variables.tf`):

1. `enable_devops_agent_integration` (bool, default: false)
   - Master switch to enable/disable DevOps Agent integration
   - When false, no EventBridge or Lambda resources are created

2. `devops_agent_webhook_secret_arn` (string, default: "")
   - ARN of AWS Secrets Manager secret containing webhook credentials
   - Required when `enable_devops_agent_integration = true`

### Secrets Manager Secret Format

The Lambda function expects a secret with this JSON structure:

```json
{
  "url": "https://event-ai.us-east-1.api.aws/webhook/generic/YOUR_WEBHOOK_ID",
  "key": "your-webhook-api-key",
  "secret": "your-webhook-secret-for-hmac"
}
```

### Setup Instructions

1. Create DevOps Agent Space in AWS Console
2. Generate generic webhook in DevOps Agent console (Capabilities tab)
3. Store webhook credentials in AWS Secrets Manager:
   ```bash
   aws secretsmanager create-secret \
     --name /autoops/dev/devops-agent-webhook \
     --secret-string '{"url":"YOUR_URL","key":"YOUR_KEY","secret":"YOUR_SECRET"}' \
     --region us-east-1
   ```
4. Update `terraform/terraform.tfvars`:
   ```hcl
   enable_devops_agent_integration  = true
   devops_agent_webhook_secret_arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:..."
   ```
5. Run `terraform apply`

## Webhook Payload Format

The Lambda function sends this payload structure:

```json
{
  "version": "1.0",
  "source": "cloudwatch-alarm",
  "timestamp": 1234567890,
  "event": {
    "type": "alarm_state_change",
    "severity": "high",
    "alarm": {
      "name": "autoops-lambda-errors-dev",
      "arn": "arn:aws:cloudwatch:...",
      "state": "ALARM",
      "previousState": "OK",
      "reason": "Threshold Crossed: 5 datapoints...",
      "region": "us-east-1",
      "accountId": "123456789012",
      "configuration": { ... }
    },
    "metadata": {
      "environment": "dev",
      "project": "autoops"
    }
  }
}
```

## Authentication

The Lambda function uses HMAC SHA-256 signature authentication:

1. Payload is serialized to JSON string
2. HMAC signature is calculated: `HMAC-SHA256(payload, secret)`
3. Request headers:
   - `Content-Type: application/json`
   - `X-Webhook-Key: <webhook_key>`
   - `X-Webhook-Signature: <hmac_signature>`
   - `User-Agent: AWS-Lambda-DevOps-Agent-Integration/1.0`

## Error Handling

- **Retry Logic**: Automatically retries on 5xx errors with exponential backoff (max 3 attempts)
- **No Retry on 4xx**: Client errors (authentication, validation) are not retried
- **Timeout**: 10-second timeout per request
- **Logging**: All errors are logged to CloudWatch Logs for debugging

## Files Created

1. `terraform/eventbridge.tf` - EventBridge rule configuration
2. `terraform/lambda_devops_agent.tf` - Lambda function and IAM resources
3. `lambda_devops_agent/lambda_function.py` - Lambda handler code
4. `lambda_devops_agent/README.md` - Lambda function documentation

## Files Modified

1. `docs/04-devops-agent-setup.md` - Updated with webhook setup instructions

## Files Unchanged (Preservation)

1. `terraform/sns.tf` - NO CHANGES (preserves email and Slack notifications)
2. `terraform/cloudwatch.tf` - NO CHANGES (preserves alarm configurations)
3. All other Terraform files - NO CHANGES

## Testing

To test the integration:

1. Enable DevOps Agent integration in `terraform.tfvars`
2. Run `terraform apply`
3. Trigger an alarm: `python tests/trigger_alarm.py`
4. Verify:
   - Email notification received ✓
   - Slack message posted via Chatbot ✓
   - Lambda function invoked (check CloudWatch Logs)
   - DevOps Agent receives webhook (check Agent console)
   - Investigation workflow starts in DevOps Agent
   - Investigation results posted to Slack

## Validation

- Terraform configuration validated: ✓
- Terraform formatting applied: ✓
- No syntax errors in Python code: ✓
- No syntax errors in Terraform files: ✓
- Documentation updated: ✓
- Preservation requirements met: ✓

## Next Steps

This implementation completes Task 3.3. The next tasks in the bugfix spec are:

- Task 3.4: Create SNS subscription for DevOps Agent (SKIPPED - not applicable with webhook architecture)
- Task 3.5: Update documentation (COMPLETED as part of this task)
- Task 3.6: Verify bug condition exploration test passes (requires deployment and testing)
- Task 3.7: Verify preservation tests still pass (requires deployment and testing)

## References

- Bugfix Spec: `.kiro/specs/slack-devops-agent-hitl-fix/bugfix.md`
- Design Document: `.kiro/specs/slack-devops-agent-hitl-fix/design.md`
- Task List: `.kiro/specs/slack-devops-agent-hitl-fix/tasks.md`
- Lambda Function README: `lambda_devops_agent/README.md`
