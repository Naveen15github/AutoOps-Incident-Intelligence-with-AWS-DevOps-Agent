# ─────────────────────────────────────────
# SNS Topic — receives CloudWatch alarms
# and forwards to your email + Slack
# ─────────────────────────────────────────
resource "aws_sns_topic" "alarms" {
  name         = "${var.project_name}-alarms-${var.environment}"
  display_name = "AutoOps Incident Alerts"
}

# Email subscription — you get an email for every alarm
resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.owner_email
}

# SNS Topic Policy — allow CloudWatch to publish
resource "aws_sns_topic_policy" "alarms" {
  arn = aws_sns_topic.alarms.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "cloudwatch.amazonaws.com" }
        Action    = "SNS:Publish"
        Resource  = aws_sns_topic.alarms.arn
      }
    ]
  })
}
