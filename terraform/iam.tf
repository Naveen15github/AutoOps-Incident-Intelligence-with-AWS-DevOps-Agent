# ─────────────────────────────────────────
# Lambda Execution Role
# ─────────────────────────────────────────
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-exec-role-${var.environment}"

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

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_iam_policy" "lambda_dynamodb" {
  name        = "${var.project_name}-lambda-dynamodb-policy-${var.environment}"
  description = "Allow Lambda to read/write DynamoDB table"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:UpdateItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.items.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_dynamodb" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_dynamodb.arn
}

# ─────────────────────────────────────────
# AWS DevOps Agent IAM Role
# This role allows DevOps Agent to READ your
# CloudWatch, X-Ray, Lambda, DynamoDB metrics
#
# NOTE: Commented out until AWS DevOps Agent
# service principal is generally available.
# The service "devops-agent.amazonaws.com" is
# currently in preview and not yet supported.
# Uncomment when GA is announced.
# ─────────────────────────────────────────
# resource "aws_iam_role" "devops_agent_role" {
#   name = "${var.project_name}-devops-agent-role-${var.environment}"
#
#   assume_role_policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Effect = "Allow"
#         Principal = {
#           Service = "devops-agent.amazonaws.com"
#         }
#         Action = "sts:AssumeRole"
#       }
#     ]
#   })
#
#   description = "Role assumed by AWS DevOps Agent to observe your infrastructure"
# }

resource "aws_iam_policy" "devops_agent_observability" {
  name        = "${var.project_name}-devops-agent-observe-policy-${var.environment}"
  description = "Grants DevOps Agent read access to observability data"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics",
          "cloudwatch:DescribeAlarms",
          "cloudwatch:DescribeAlarmHistory",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:GetLogEvents",
          "logs:FilterLogEvents",
          "logs:StartQuery",
          "logs:GetQueryResults",
          "xray:GetTraceSummaries",
          "xray:BatchGetTraces",
          "xray:GetServiceGraph",
          "xray:GetTraceGraph",
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration",
          "lambda:ListFunctions",
          "dynamodb:DescribeTable",
          "dynamodb:ListTables",
          "apigateway:GET",
          "tag:GetResources"
        ]
        Resource = "*"
      }
    ]
  })
}

# resource "aws_iam_role_policy_attachment" "devops_agent_observe" {
#   role       = aws_iam_role.devops_agent_role.name
#   policy_arn = aws_iam_policy.devops_agent_observability.arn
# }

# ─────────────────────────────────────────
# ChatBot (Slack) IAM Role for SNS Notifications
# ─────────────────────────────────────────
resource "aws_iam_role" "chatbot_role" {
  name = "${var.project_name}-chatbot-slack-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "chatbot.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "chatbot_readonly" {
  role       = aws_iam_role.chatbot_role.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}
