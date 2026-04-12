# ─────────────────────────────────────────────────────────────────────
# Lambda Function for DevOps Agent Webhook Integration
#
# This Lambda function receives CloudWatch alarm events from EventBridge
# and forwards them to the AWS DevOps Agent webhook endpoint with proper
# HMAC authentication for autonomous incident investigation.
# ─────────────────────────────────────────────────────────────────────

resource "aws_lambda_function" "devops_agent_webhook" {
  count = var.enable_devops_agent_integration ? 1 : 0

  function_name = "${var.project_name}-devops-agent-webhook-${var.environment}"
  description   = "Forward CloudWatch alarm events to DevOps Agent webhook"
  role          = aws_iam_role.devops_agent_lambda_exec[0].arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  memory_size   = 256
  timeout       = 30

  s3_bucket        = aws_s3_bucket.lambda_artifacts.id
  s3_key           = aws_s3_object.devops_agent_lambda_zip[0].key
  source_code_hash = data.archive_file.devops_agent_lambda_zip[0].output_base64sha256

  environment {
    variables = {
      WEBHOOK_SECRET_ARN = var.devops_agent_webhook_secret_arn
      ENVIRONMENT        = var.environment
      PROJECT_NAME       = var.project_name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.devops_agent_lambda_basic,
    aws_iam_role_policy_attachment.devops_agent_lambda_secrets,
    aws_cloudwatch_log_group.devops_agent_lambda_logs,
  ]
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "devops_agent_lambda_logs" {
  count = var.enable_devops_agent_integration ? 1 : 0

  name              = "/aws/lambda/${var.project_name}-devops-agent-webhook-${var.environment}"
  retention_in_days = 14
}

# Package Lambda function code
data "archive_file" "devops_agent_lambda_zip" {
  count = var.enable_devops_agent_integration ? 1 : 0

  type        = "zip"
  source_dir  = "${path.module}/../lambda_devops_agent"
  output_path = "${path.module}/../.terraform/lambda_devops_agent.zip"
}

resource "aws_s3_object" "devops_agent_lambda_zip" {
  count = var.enable_devops_agent_integration ? 1 : 0

  bucket = aws_s3_bucket.lambda_artifacts.id
  key    = "lambda_devops_agent_${data.archive_file.devops_agent_lambda_zip[0].output_md5}.zip"
  source = data.archive_file.devops_agent_lambda_zip[0].output_path
  etag   = data.archive_file.devops_agent_lambda_zip[0].output_md5
}

# ─────────────────────────────────────────────────────────────────────
# IAM Role for DevOps Agent Lambda Function
# ─────────────────────────────────────────────────────────────────────

resource "aws_iam_role" "devops_agent_lambda_exec" {
  count = var.enable_devops_agent_integration ? 1 : 0

  name = "${var.project_name}-devops-agent-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "devops_agent_lambda_basic" {
  count = var.enable_devops_agent_integration ? 1 : 0

  role       = aws_iam_role.devops_agent_lambda_exec[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# IAM policy to read webhook credentials from Secrets Manager
resource "aws_iam_policy" "devops_agent_lambda_secrets" {
  count = var.enable_devops_agent_integration ? 1 : 0

  name        = "${var.project_name}-devops-agent-lambda-secrets-${var.environment}"
  description = "Allow Lambda to read DevOps Agent webhook credentials from Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = var.devops_agent_webhook_secret_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "devops_agent_lambda_secrets" {
  count = var.enable_devops_agent_integration ? 1 : 0

  role       = aws_iam_role.devops_agent_lambda_exec[0].name
  policy_arn = aws_iam_policy.devops_agent_lambda_secrets[0].arn
}
