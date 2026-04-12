# ─────────────────────────────────────────
# CloudWatch Alarms
# These alarms feed AWS DevOps Agent —
# when one fires, the Agent wakes up and
# starts autonomous investigation
# ─────────────────────────────────────────

# Alarm 1 — Lambda Errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors-${var.environment}"
  alarm_description   = "Lambda function error rate is too high — triggers DevOps Agent investigation"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = var.alarm_error_threshold

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }

  alarm_actions             = [aws_sns_topic.alarms.arn]
  ok_actions                = [aws_sns_topic.alarms.arn]
  insufficient_data_actions = []

  treat_missing_data = "notBreaching"
}

# Alarm 2 — Lambda Duration (P99 latency)
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.project_name}-lambda-high-duration-${var.environment}"
  alarm_description   = "Lambda P99 duration is above 10 seconds — possible DynamoDB issue"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 60
  extended_statistic  = "p99"
  threshold           = 10000 # 10 seconds in ms

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  treat_missing_data = "notBreaching"
}

# Alarm 3 — Lambda Throttles
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${var.project_name}-lambda-throttles-${var.environment}"
  alarm_description   = "Lambda function is being throttled"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 1

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  treat_missing_data = "notBreaching"
}

# Alarm 4 — DynamoDB Write Throttles (THE KEY ALARM)
# This is what DevOps Agent will detect and diagnose
resource "aws_cloudwatch_metric_alarm" "dynamodb_write_throttles" {
  alarm_name          = "${var.project_name}-dynamodb-write-throttles-${var.environment}"
  alarm_description   = "DynamoDB write requests are being throttled — DevOps Agent will diagnose"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 60
  statistic           = "Sum"
  threshold           = var.alarm_throttle_threshold

  dimensions = {
    TableName = aws_dynamodb_table.items.name
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  treat_missing_data = "notBreaching"
}

# Alarm 5 — DynamoDB Read Throttles
resource "aws_cloudwatch_metric_alarm" "dynamodb_read_throttles" {
  alarm_name          = "${var.project_name}-dynamodb-read-throttles-${var.environment}"
  alarm_description   = "DynamoDB read requests are being throttled"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 60
  statistic           = "Sum"
  threshold           = var.alarm_throttle_threshold

  dimensions = {
    TableName = aws_dynamodb_table.items.name
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  treat_missing_data = "notBreaching"
}

# Alarm 6 — API Gateway 5XX Errors
resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  alarm_name          = "${var.project_name}-api-5xx-errors-${var.environment}"
  alarm_description   = "API Gateway is returning 5XX server errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 60
  statistic           = "Sum"
  threshold           = 5

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  treat_missing_data = "notBreaching"
}

# ─────────────────────────────────────────
# CloudWatch Dashboard
# ─────────────────────────────────────────
resource "aws_cloudwatch_dashboard" "autoops" {
  dashboard_name = "${var.project_name}-dashboard-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Lambda — Errors & Throttles"
          view   = "timeSeries"
          region = var.aws_region
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.api.function_name],
            ["AWS/Lambda", "Throttles", "FunctionName", aws_lambda_function.api.function_name]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "DynamoDB — Throttle Events"
          view   = "timeSeries"
          region = var.aws_region
          metrics = [
            ["AWS/DynamoDB", "WriteThrottleEvents", "TableName", aws_dynamodb_table.items.name],
            ["AWS/DynamoDB", "ReadThrottleEvents", "TableName", aws_dynamodb_table.items.name]
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Lambda — Duration P99"
          view   = "timeSeries"
          region = var.aws_region
          metrics = [
            [{ expression = "ANOMALY_DETECTION_BAND(m1, 2)", label = "Expected (normal band)", id = "e1" }],
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.api.function_name, { id = "m1", stat = "p99" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "API Gateway — Request Count & 5XX Errors"
          view   = "timeSeries"
          region = var.aws_region
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.main.name, "Stage", var.environment],
            ["AWS/ApiGateway", "5XXError", "ApiName", aws_api_gateway_rest_api.main.name, "Stage", var.environment]
          ]
        }
      }
    ]
  })
}
