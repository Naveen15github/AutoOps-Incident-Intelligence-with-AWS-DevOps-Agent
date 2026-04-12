output "api_endpoint" {
  description = "Your API Gateway URL — use this in tests and website config"
  value       = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.api.function_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.items.name
}

# output "devops_agent_role_arn" {
#   description = "IMPORTANT: Paste this into AWS DevOps Agent console when creating Agent Space"
#   value       = aws_iam_role.devops_agent_role.arn
# }

output "sns_topic_arn" {
  description = "SNS topic ARN for alarm notifications"
  value       = aws_sns_topic.alarms.arn
}

output "cloudwatch_dashboard_url" {
  description = "Direct link to your CloudWatch dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.autoops.dashboard_name}"
}

output "lambda_log_group" {
  description = "CloudWatch log group for Lambda function"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "s3_artifact_bucket" {
  description = "S3 bucket storing Lambda deployment package"
  value       = aws_s3_bucket.lambda_artifacts.bucket
}

output "account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "next_steps" {
  description = "What to do after terraform apply"
  value       = <<-EOT
    ✅ Infrastructure deployed!

    NEXT STEPS:
    1. Confirm SNS subscription in your email: ${var.owner_email}
    2. Set up Slack → read docs/03-slack-setup.md
    3. Create DevOps Agent Space → read docs/04-devops-agent-setup.md
       NOTE: Create the DevOps Agent IAM role manually in AWS Console
       Attach this policy ARN: ${aws_iam_policy.devops_agent_observability.arn}
    4. Test your API: cd tests && python test_api.py
    5. Trigger an incident: python tests/trigger_throttle.py

    Your API URL:
    https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}
  EOT
}
