"""
Lambda function to forward CloudWatch alarm events to AWS DevOps Agent webhook.

This function:
1. Receives CloudWatch alarm state change events from EventBridge
2. Retrieves webhook credentials from AWS Secrets Manager
3. Formats the alarm data for DevOps Agent webhook
4. Calculates HMAC SHA-256 signature for authentication
5. POSTs the event to the DevOps Agent webhook endpoint
6. Handles errors and implements retry logic
"""

import json
import os
import hmac
import hashlib
import time
import boto3
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Initialize AWS clients
secrets_client = boto3.client('secretsmanager')

def lambda_handler(event, context):
    """
    Main Lambda handler for DevOps Agent webhook integration.
    
    Args:
        event: EventBridge event containing CloudWatch alarm state change
        context: Lambda context object
        
    Returns:
        dict: Response with status code and message
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract alarm details from EventBridge event
        alarm_data = extract_alarm_data(event)
        print(f"Extracted alarm data: {json.dumps(alarm_data)}")
        
        # Get webhook credentials from Secrets Manager
        webhook_config = get_webhook_credentials()
        
        # Format payload for DevOps Agent webhook
        payload = format_webhook_payload(alarm_data)
        
        # Generate ISO 8601 timestamp for signature
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
        
        # Calculate HMAC signature
        signature = calculate_hmac_signature(
            payload=json.dumps(payload),
            secret=webhook_config['secret'],
            timestamp=timestamp
        )
        
        # Send to DevOps Agent webhook
        response = send_to_webhook(
            url=webhook_config['url'],
            payload=payload,
            webhook_key=webhook_config['key'],
            signature=signature,
            timestamp=timestamp
        )
        
        print(f"Successfully sent alarm to DevOps Agent: {response}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Alarm forwarded to DevOps Agent',
                'alarmName': alarm_data['alarmName']
            })
        }
        
    except Exception as e:
        print(f"Error processing alarm event: {str(e)}")
        raise


def extract_alarm_data(event):
    """
    Extract relevant alarm information from EventBridge event.
    
    Args:
        event: EventBridge event
        
    Returns:
        dict: Extracted alarm data
    """
    detail = event.get('detail', {})
    
    return {
        'alarmName': detail.get('alarmName', 'Unknown'),
        'state': detail.get('state', {}).get('value', 'UNKNOWN'),
        'previousState': detail.get('previousState', {}).get('value', 'UNKNOWN'),
        'reason': detail.get('state', {}).get('reason', ''),
        'timestamp': detail.get('state', {}).get('timestamp', ''),
        'region': event.get('region', os.environ.get('AWS_REGION', 'us-east-1')),
        'accountId': event.get('account', ''),
        'alarmArn': detail.get('alarmArn', ''),
        'configuration': detail.get('configuration', {}),
    }


def get_webhook_credentials():
    """
    Retrieve DevOps Agent webhook credentials from Secrets Manager.
    
    Returns:
        dict: Webhook configuration with 'url', 'key', and 'secret'
    """
    secret_arn = os.environ.get('WEBHOOK_SECRET_ARN')
    
    if not secret_arn:
        raise ValueError("WEBHOOK_SECRET_ARN environment variable not set")
    
    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret_string = response['SecretString']
        credentials = json.loads(secret_string)
        
        # Validate required fields
        required_fields = ['url', 'key', 'secret']
        for field in required_fields:
            if field not in credentials:
                raise ValueError(f"Missing required field '{field}' in webhook credentials")
        
        return credentials
        
    except Exception as e:
        print(f"Error retrieving webhook credentials: {str(e)}")
        raise


def format_webhook_payload(alarm_data):
    """
    Format alarm data into DevOps Agent webhook payload format.
    
    AWS DevOps Agent expects a specific payload format:
    - eventType: Type of event (e.g., 'incident')
    - incidentId: Unique identifier for the incident
    - action: Action type (e.g., 'created')
    - priority: Priority level (HIGH, MEDIUM, LOW)
    - title: Short incident title
    - description: Detailed description
    - service: Service name
    - timestamp: ISO 8601 timestamp
    
    Args:
        alarm_data: Extracted alarm data
        
    Returns:
        dict: Formatted payload for webhook
    """
    # Generate unique incident ID from alarm name and timestamp
    incident_id = f"{alarm_data['alarmName']}-{int(time.time())}"
    
    # Map alarm state to priority
    priority = 'HIGH' if alarm_data['state'] == 'ALARM' else 'LOW'
    
    # Format timestamp as ISO 8601
    timestamp = alarm_data['timestamp'] if alarm_data['timestamp'] else time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
    
    return {
        'eventType': 'incident',
        'incidentId': incident_id,
        'action': 'created',
        'priority': priority,
        'title': f"CloudWatch Alarm: {alarm_data['alarmName']}",
        'description': f"{alarm_data['reason']}\n\nAlarm: {alarm_data['alarmName']}\nState: {alarm_data['previousState']} → {alarm_data['state']}\nRegion: {alarm_data['region']}\nAccount: {alarm_data['accountId']}",
        'service': os.environ.get('PROJECT_NAME', 'autoops'),
        'timestamp': timestamp,
        'data': {
            'metadata': {
                'environment': os.environ.get('ENVIRONMENT', 'dev'),
                'region': alarm_data['region'],
                'alarmArn': alarm_data['alarmArn'],
                'configuration': alarm_data['configuration'],
            }
        }
    }


def calculate_hmac_signature(payload, secret, timestamp):
    """
    Calculate HMAC SHA-256 signature for AWS DevOps Agent webhook authentication.
    
    AWS DevOps Agent expects the signature to be calculated as:
    HMAC-SHA256(timestamp:payload) encoded in base64
    
    Args:
        payload: JSON string payload
        secret: Webhook secret key
        timestamp: ISO 8601 timestamp string
        
    Returns:
        str: Base64-encoded HMAC signature
    """
    # Create the message to sign: timestamp:payload
    message = f"{timestamp}:{payload}"
    message_bytes = message.encode('utf-8')
    secret_bytes = secret.encode('utf-8')
    
    # Calculate HMAC-SHA256 and encode as base64
    signature = hmac.new(
        secret_bytes,
        message_bytes,
        hashlib.sha256
    ).digest()
    
    # Return base64-encoded signature
    import base64
    return base64.b64encode(signature).decode('utf-8')


def send_to_webhook(url, payload, webhook_key, signature, timestamp, max_retries=3):
    """
    Send payload to DevOps Agent webhook with retry logic.
    
    AWS DevOps Agent expects:
    - Header: x-amzn-event-timestamp (ISO 8601 format)
    - Header: x-amzn-event-signature (base64-encoded HMAC-SHA256)
    - Header: Content-Type: application/json
    
    Args:
        url: Webhook URL
        payload: Formatted payload dict
        webhook_key: Webhook API key (not used in HMAC v1, kept for compatibility)
        signature: HMAC signature
        timestamp: ISO 8601 timestamp
        max_retries: Maximum number of retry attempts
        
    Returns:
        dict: Response from webhook
    """
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode('utf-8')
    
    headers = {
        'Content-Type': 'application/json',
        'x-amzn-event-timestamp': timestamp,
        'x-amzn-event-signature': signature,
        'User-Agent': 'AWS-Lambda-DevOps-Agent-Integration/1.0'
    }
    
    for attempt in range(max_retries):
        try:
            request = Request(url, data=payload_bytes, headers=headers, method='POST')
            
            with urlopen(request, timeout=10) as response:
                response_body = response.read().decode('utf-8')
                
                return {
                    'status': response.status,
                    'body': response_body
                }
                
        except HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else 'No error body'
            print(f"HTTP error on attempt {attempt + 1}/{max_retries}: {e.code} - {error_body}")
            
            # Don't retry on client errors (4xx)
            if 400 <= e.code < 500:
                raise
            
            # Retry on server errors (5xx)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
            
        except URLError as e:
            print(f"URL error on attempt {attempt + 1}/{max_retries}: {str(e)}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
            
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}/{max_retries}: {str(e)}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    
    raise Exception(f"Failed to send webhook after {max_retries} attempts")
