variable "aws_region" {
  description = "AWS region to deploy all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "owner_email" {
  description = "Your email address — used for SNS alarm notifications"
  type        = string
  # FILL THIS IN: example → "yourname@gmail.com"
}

variable "project_name" {
  description = "Project name used as prefix for all resources"
  type        = string
  default     = "autoops"
}

variable "slack_workspace_id" {
  description = "Slack Workspace ID (from Step 3 of Slack setup guide)"
  type        = string
  default     = ""
}

variable "slack_channel_id" {
  description = "Slack Channel ID (from Step 3 of Slack setup guide)"
  type        = string
  default     = ""
}

variable "dynamodb_read_capacity" {
  description = "DynamoDB read capacity units (keep at 1 for free tier + throttle demo)"
  type        = number
  default     = 1
}

variable "dynamodb_write_capacity" {
  description = "DynamoDB write capacity units (keep at 1 for free tier + throttle demo)"
  type        = number
  default     = 1
}

variable "lambda_memory_mb" {
  description = "Lambda memory in MB"
  type        = number
  default     = 256
}

variable "lambda_timeout_seconds" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 30
}

variable "alarm_error_threshold" {
  description = "Lambda error count that triggers CloudWatch alarm"
  type        = number
  default     = 5
}

variable "alarm_throttle_threshold" {
  description = "DynamoDB throttle count that triggers alarm"
  type        = number
  default     = 1
}

# ─────────────────────────────────────────────────────────────────────
# DevOps Agent Integration Variables
# ─────────────────────────────────────────────────────────────────────

variable "devops_agent_webhook_secret_arn" {
  description = "ARN of AWS Secrets Manager secret containing DevOps Agent webhook credentials (url, key, secret). Leave empty to disable DevOps Agent integration. The webhook uses EventBridge → Lambda → DevOps Agent architecture for autonomous incident investigation."
  type        = string
  default     = ""
}

variable "enable_devops_agent_integration" {
  description = "Enable DevOps Agent integration for autonomous incident investigation. When enabled, CloudWatch alarms trigger EventBridge → Lambda → DevOps Agent webhook flow. Requires devops_agent_webhook_secret_arn to be configured."
  type        = bool
  default     = false
}
