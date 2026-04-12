# ─────────────────────────────────────────────────────────────────────
# EventBridge Rule for DevOps Agent Integration
#
# CloudWatch alarms automatically send state change events to EventBridge.
# This rule captures ALARM state changes and triggers the Lambda function
# that calls the DevOps Agent webhook for autonomous investigation.
# ─────────────────────────────────────────────────────────────────────

resource "aws_cloudwatch_event_rule" "alarm_state_change" {
  count = var.enable_devops_agent_integration ? 1 : 0

  name        = "${var.project_name}-alarm-to-devops-agent-${var.environment}"
  description = "Capture CloudWatch alarm state changes and forward to DevOps Agent webhook"

  event_pattern = jsonencode({
    source      = ["aws.cloudwatch"]
    detail-type = ["CloudWatch Alarm State Change"]
    detail = {
      state = {
        value = ["ALARM"]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "devops_agent_lambda" {
  count = var.enable_devops_agent_integration ? 1 : 0

  rule      = aws_cloudwatch_event_rule.alarm_state_change[0].name
  target_id = "DevOpsAgentWebhookLambda"
  arn       = aws_lambda_function.devops_agent_webhook[0].arn
}

# Lambda permission to allow EventBridge to invoke the function
resource "aws_lambda_permission" "eventbridge_invoke" {
  count = var.enable_devops_agent_integration ? 1 : 0

  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.devops_agent_webhook[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.alarm_state_change[0].arn
}
