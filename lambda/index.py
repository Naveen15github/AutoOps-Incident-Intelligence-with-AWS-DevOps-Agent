"""
AutoOps — Intelligent Incident Response Platform
Lambda Function Handler

This is the serverless API backend that AWS DevOps Agent monitors.
It's a simple Items CRUD API backed by DynamoDB.

The low DynamoDB capacity (1 WCU) means the throttle test will
easily trigger CloudWatch alarms → DevOps Agent investigation.
"""

import json
import os
import uuid
import time
import logging
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients — initialized once at cold start for reuse
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])

ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
PROJECT_NAME = os.environ.get("PROJECT_NAME", "autoops")


def lambda_handler(event, context):
    """Main entry point — routes HTTP requests to handler functions."""
    start_time = time.time()

    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/")
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    body_raw = event.get("body", "{}")

    logger.info(json.dumps({
        "event": "request_received",
        "method": http_method,
        "path": path,
        "request_id": context.aws_request_id,
        "environment": ENVIRONMENT,
    }))

    try:
        body = json.loads(body_raw) if body_raw else {}
    except json.JSONDecodeError:
        body = {}

    # ── Route matching ──────────────────────────────────────────
    if path == "/health" and http_method == "GET":
        response = handle_health(context)
    elif path == "/items" and http_method == "GET":
        response = handle_list_items(query_params)
    elif path == "/items" and http_method == "POST":
        response = handle_create_item(body)
    elif path_params.get("itemId") and http_method == "GET":
        response = handle_get_item(path_params["itemId"])
    elif path_params.get("itemId") and http_method == "DELETE":
        response = handle_delete_item(path_params["itemId"])
    elif path == "/simulate-error" and http_method == "POST":
        response = handle_simulate_error(body)
    else:
        response = error_response(404, "Route not found", f"{http_method} {path}")

    # Log duration for CloudWatch metrics
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(json.dumps({
        "event": "request_completed",
        "method": http_method,
        "path": path,
        "status_code": response["statusCode"],
        "duration_ms": duration_ms,
        "request_id": context.aws_request_id,
    }))

    return response


# ── Handlers ────────────────────────────────────────────────────────

def handle_health(context):
    """Health check — used by tests to verify the API is up."""
    return success_response({
        "status": "healthy",
        "service": "autoops-api",
        "environment": ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "lambda_version": context.function_version,
        "remaining_time_ms": context.get_remaining_time_in_millis(),
    })


def handle_list_items(query_params):
    """List all items from DynamoDB."""
    try:
        limit = int(query_params.get("limit", "20"))
        result = table.scan(Limit=min(limit, 100))
        items = result.get("Items", [])

        logger.info(json.dumps({
            "event": "items_listed",
            "count": len(items),
        }))

        return success_response({
            "items": items,
            "count": len(items),
        })
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(json.dumps({
            "event": "dynamodb_error",
            "error_code": error_code,
            "error_message": str(e),
        }))
        if error_code == "ProvisionedThroughputExceededException":
            return error_response(503, "Database is temporarily overloaded", "DynamoDB throttle — DevOps Agent should detect this")
        return error_response(500, "Database error", error_code)


def handle_create_item(body):
    """Create a new item in DynamoDB."""
    item_id = str(uuid.uuid4())
    name = body.get("name", f"Item-{item_id[:8]}")
    category = body.get("category", "general")
    price = body.get("price", 0)

    item = {
        "itemId": item_id,
        "name": name,
        "category": category,
        "price": str(price),
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "status": "active",
    }

    try:
        table.put_item(Item=item)
        logger.info(json.dumps({
            "event": "item_created",
            "item_id": item_id,
            "name": name,
        }))
        return success_response({"message": "Item created", "item": item}, status_code=201)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(json.dumps({
            "event": "dynamodb_write_error",
            "error_code": error_code,
            "error_message": str(e),
        }))
        if error_code == "ProvisionedThroughputExceededException":
            return error_response(503, "Write capacity exceeded", "DynamoDB throttle on write — DevOps Agent will detect this!")
        return error_response(500, "Failed to create item", error_code)


def handle_get_item(item_id):
    """Retrieve a single item by ID."""
    try:
        result = table.get_item(Key={"itemId": item_id})
        item = result.get("Item")
        if not item:
            return error_response(404, "Item not found", item_id)
        return success_response({"item": item})
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(json.dumps({
            "event": "dynamodb_read_error",
            "error_code": error_code,
            "item_id": item_id,
        }))
        return error_response(500, "Failed to retrieve item", error_code)


def handle_delete_item(item_id):
    """Delete an item by ID."""
    try:
        table.delete_item(Key={"itemId": item_id})
        logger.info(json.dumps({"event": "item_deleted", "item_id": item_id}))
        return success_response({"message": "Item deleted", "itemId": item_id})
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        return error_response(500, "Failed to delete item", error_code)


def handle_simulate_error(body):
    """
    Simulate different error types for DevOps Agent demo purposes.
    POST /simulate-error with {"type": "throttle"|"timeout"|"error"}
    """
    error_type = body.get("type", "error")

    if error_type == "timeout":
        # Simulate a slow response
        time.sleep(15)
        return success_response({"message": "Simulated timeout completed (slow path)"})
    elif error_type == "crash":
        # Force a 500 error
        raise RuntimeError("Simulated crash — this will appear in CloudWatch Logs and trigger DevOps Agent!")
    elif error_type == "throttle":
        # Simulate what a throttle error looks like
        return error_response(503, "Simulated DynamoDB throttle",
                              "ProvisionedThroughputExceededException (simulated)")
    else:
        return error_response(500, "Simulated internal error",
                              "Intentional error for DevOps Agent demo")


# ── Response helpers ─────────────────────────────────────────────────

def success_response(data, status_code=200):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "X-Service": "autoops-api",
        },
        "body": json.dumps(data),
    }


def error_response(status_code, message, detail=""):
    logger.error(json.dumps({
        "event": "error_response",
        "status_code": status_code,
        "message": message,
        "detail": detail,
    }))
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({
            "error": message,
            "detail": detail,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }),
    }
