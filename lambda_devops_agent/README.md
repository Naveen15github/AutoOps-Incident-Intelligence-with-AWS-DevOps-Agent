# DevOps Agent Webhook Lambda Function

This Lambda function forwards CloudWatch alarm events to the AWS DevOps Agent webhook for autonomous incident investigation.

## Architecture

```
CloudWatch Alarm → EventBridge (automatic) → Lambda Function → DevOps Agent Webhook
```

## How It Works

1. **CloudWatch alarms** automatically send state change events to EventBridge (no configuration needed)
2. **EventBridge rule** filters for ALARM state changes and triggers this Lambda function
3. **Lambda function**:
   - Retrieves webhook credentials from AWS Secrets Manager
   - Formats alarm data for DevOps Agent webhook
   - Calculates HMAC SHA-256 signature for authentication
   - POSTs to DevOps Agent webhook endpoint
   - Handles errors and retries

## Webhook Credentials

The Lambda function expects a secret in AWS Secrets Manager with the following JSON structure:

```json
{
  "url": "https://event-ai.us-east-1.api.aws/webhook/generic/YOUR_WEBHOOK_ID",
  "key": "your-webhook-api-key",
  "secret": "your-webhook-secret-for-hmac"
}
```

The secret ARN is passed via the `WEBHOOK_SECRET_ARN` environment variable.

## Webhook Authentication

The function uses HMAC SHA-256 signature authentication:

1. Payload is serialized to JSON string
2. HMAC signature is calculated: `HMAC-SHA256(payload, secret)`
3. Signature is sent in `X-Webhook-Signature` header
4. API key is sent in `X-Webhook-Key` header

## Payload Format

The function sends a structured payload to the webhook:

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

## Error Handling

- **Retry Logic**: Automatically retries on 5xx errors with exponential backoff (max 3 attempts)
- **No Retry on 4xx**: Client errors (authentication, validation) are not retried
- **Timeout**: 10-second timeout per request
- **Logging**: All errors are logged to CloudWatch Logs for debugging

## Environment Variables

- `WEBHOOK_SECRET_ARN`: ARN of Secrets Manager secret containing webhook credentials
- `ENVIRONMENT`: Environment name (dev, staging, prod)
- `PROJECT_NAME`: Project name for metadata
- `AWS_REGION`: AWS region (automatically set by Lambda)

## IAM Permissions Required

The Lambda execution role needs:
- `secretsmanager:GetSecretValue` on the webhook secret
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` for CloudWatch Logs

## Testing

To test the function locally, you can invoke it with a sample EventBridge event:

```python
import json
from lambda_function import lambda_handler

event = {
    "version": "0",
    "id": "test-event-id",
    "detail-type": "CloudWatch Alarm State Change",
    "source": "aws.cloudwatch",
    "account": "123456789012",
    "region": "us-east-1",
    "detail": {
        "alarmName": "autoops-lambda-errors-dev",
        "state": {
            "value": "ALARM",
            "reason": "Threshold Crossed: 5 datapoints...",
            "timestamp": "2024-01-15T10:30:00.000Z"
        },
        "previousState": {
            "value": "OK"
        },
        "alarmArn": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:autoops-lambda-errors-dev",
        "configuration": {}
    }
}

result = lambda_handler(event, None)
print(json.dumps(result, indent=2))
```

## Deployment

This function is deployed automatically by Terraform when `var.enable_devops_agent_integration = true`.

See `terraform/lambda_devops_agent.tf` for the Terraform configuration.
