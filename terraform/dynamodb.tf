# ─────────────────────────────────────────
# DynamoDB Table
# Intentionally LOW capacity (1 RCU/WCU)
# so the throttle test triggers quickly —
# this is what DevOps Agent will detect!
# ─────────────────────────────────────────
resource "aws_dynamodb_table" "items" {
  name           = "${var.project_name}-items-${var.environment}"
  billing_mode   = "PROVISIONED"
  read_capacity  = var.dynamodb_read_capacity
  write_capacity = var.dynamodb_write_capacity
  hash_key       = "itemId"

  attribute {
    name = "itemId"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-items-table"
  }
}
