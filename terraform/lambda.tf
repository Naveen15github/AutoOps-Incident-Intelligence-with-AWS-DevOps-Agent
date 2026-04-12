# ─────────────────────────────────────────
# Lambda Function
# ─────────────────────────────────────────
resource "aws_lambda_function" "api" {
  function_name = "${var.project_name}-api-${var.environment}"
  description   = "AutoOps API — monitored by AWS DevOps Agent"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "index.lambda_handler"
  runtime       = "python3.12"
  memory_size   = var.lambda_memory_mb
  timeout       = var.lambda_timeout_seconds

  s3_bucket        = aws_s3_bucket.lambda_artifacts.id
  s3_key           = aws_s3_object.lambda_zip.key
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.items.name
      ENVIRONMENT    = var.environment
      PROJECT_NAME   = var.project_name
    }
  }

  # Enable X-Ray active tracing — critical for DevOps Agent correlation
  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_xray,
    aws_iam_role_policy_attachment.lambda_dynamodb,
    aws_cloudwatch_log_group.lambda_logs,
  ]
}

# CloudWatch Log Group for Lambda
# Explicit resource so Terraform manages its lifecycle
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-api-${var.environment}"
  retention_in_days = 14
}

# Lambda Permission — allow API Gateway to invoke Lambda
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}
