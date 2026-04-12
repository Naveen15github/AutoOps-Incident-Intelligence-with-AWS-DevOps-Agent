# ─────────────────────────────────────────
# AWS DevOps Agent Configuration
#
# NOTE: AWS DevOps Agent is a managed service
# that does NOT yet have a native Terraform
# resource (as of 2026). We use null_resource
# with AWS CLI to automate what we can.
#
# Slack integration must still be done via
# the AWS Console (guided in docs/03-slack-setup.md)
#
# IMPORTANT: The DevOps Agent IAM role is currently
# commented out in iam.tf because the service principal
# "devops-agent.amazonaws.com" is not yet GA.
# You'll need to create the role manually in the console
# when setting up the DevOps Agent Space.
# ─────────────────────────────────────────

# Store DevOps Agent Role ARN in SSM for easy reference
# NOTE: Commented out until DevOps Agent role is available
# resource "aws_ssm_parameter" "devops_agent_role_arn" {
#   name        = "/${var.project_name}/${var.environment}/devops-agent-role-arn"
#   type        = "String"
#   value       = aws_iam_role.devops_agent_role.arn
#   description = "IAM Role ARN to paste into AWS DevOps Agent console"
#
#   tags = {
#     Name = "DevOps Agent Role ARN"
#   }
# }

resource "aws_ssm_parameter" "api_endpoint" {
  name        = "/${var.project_name}/${var.environment}/api-endpoint"
  type        = "String"
  value       = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
  description = "API Gateway endpoint URL"
}

resource "aws_ssm_parameter" "dynamodb_table_name" {
  name        = "/${var.project_name}/${var.environment}/dynamodb-table-name"
  type        = "String"
  value       = aws_dynamodb_table.items.name
  description = "DynamoDB table name for reference"
}

# ─────────────────────────────────────────
# CloudWatch Alarm ARNs stored for DevOps Agent registration
# ─────────────────────────────────────────
resource "aws_ssm_parameter" "alarm_arns" {
  name = "/${var.project_name}/${var.environment}/alarm-arns"
  type = "StringList"
  value = join(",", [
    aws_cloudwatch_metric_alarm.lambda_errors.arn,
    aws_cloudwatch_metric_alarm.lambda_duration.arn,
    aws_cloudwatch_metric_alarm.lambda_throttles.arn,
    aws_cloudwatch_metric_alarm.dynamodb_write_throttles.arn,
    aws_cloudwatch_metric_alarm.dynamodb_read_throttles.arn,
    aws_cloudwatch_metric_alarm.api_5xx.arn,
  ])
  description = "CloudWatch alarm ARNs to connect to DevOps Agent Space"
}

# ─────────────────────────────────────────
# null_resource: prints the exact console
# steps you need to complete after terraform apply
# ─────────────────────────────────────────
resource "null_resource" "devops_agent_instructions" {
  triggers = {
    lambda_name   = aws_lambda_function.api.function_name
    dynamodb_name = aws_dynamodb_table.items.name
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo ""
      echo "════════════════════════════════════════════════════════════"
      echo "  TERRAFORM APPLY COMPLETE — ACTION REQUIRED"
      echo "════════════════════════════════════════════════════════════"
      echo ""
      echo "  Your AWS infrastructure is ready. Now complete these"
      echo "  3 manual steps in the AWS Console:"
      echo ""
      echo "  STEP 1: SLACK SETUP"
      echo "  → Open docs/03-slack-setup.md for complete guide"
      echo ""
      echo "  STEP 2: DEVOPS AGENT SPACE CREATION"
      echo "  → Go to: https://console.aws.amazon.com/devops-agent"
      echo "  → Click: Create Agent Space"
      echo "  → Create IAM role manually (devops-agent.amazonaws.com not yet GA)"
      echo "  → Attach policy: ${aws_iam_policy.devops_agent_observability.arn}"
      echo ""
      echo "  STEP 3: CONNECT YOUR RESOURCES"
      echo "  → Lambda Function: ${aws_lambda_function.api.function_name}"
      echo "  → DynamoDB Table:  ${aws_dynamodb_table.items.name}"
      echo "  → CloudWatch Alarms: All 6 autoops-* alarms"
      echo ""
      echo "  STEP 4: RUN TESTS"
      echo "  → cd tests && python test_api.py"
      echo "  → python trigger_throttle.py (triggers DevOps Agent!)"
      echo ""
      echo "════════════════════════════════════════════════════════════"
    EOT
  }

  depends_on = [
    aws_lambda_function.api,
    aws_dynamodb_table.items,
  ]
}
