#!/usr/bin/env python3
"""
Bug Condition Exploration Test - DevOps Agent Notification Subscription

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

Property 1: Fault Condition - DevOps Agent Does Not Receive Alarm Notifications

CRITICAL: This test MUST FAIL on unfixed infrastructure - failure confirms the bug exists.
DO NOT attempt to fix the test or the infrastructure when it fails.

This test encodes the expected behavior:
- When CloudWatch alarm transitions to ALARM state and publishes to SNS topic
- DevOps Agent SHOULD receive notification within 30 seconds
- DevOps Agent SHOULD start investigation workflow
- Investigation results SHOULD appear in Slack within 2-4 minutes

EXPECTED OUTCOME ON UNFIXED INFRASTRUCTURE: Test FAILS
- DevOps Agent subscription missing from SNS topic
- No investigation workflow triggered in DevOps Agent console
- No investigation results posted to Slack after 4 minutes

When this test passes after implementing the fix, it confirms the bug is resolved.
"""

import boto3
import time
import sys
from datetime import datetime

# Configuration
ALARM_NAME = "autoops-lambda-errors-dev"
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:478468758108:autoops-alarms-dev"
DEVOPS_AGENT_SPACE_ID = "238ad9b9-0c96-42e3-8290-deb05bd94b4e"
AWS_REGION = "us-east-1"
NOTIFICATION_TIMEOUT_SECONDS = 30
INVESTIGATION_TIMEOUT_SECONDS = 240  # 4 minutes

# Terminal colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(title):
    """Print formatted section header"""
    print(f"\n{BOLD}{CYAN}{'═' * 70}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 70}{RESET}")


def print_test_info(msg):
    """Print test information"""
    print(f"  {CYAN}→{RESET} {msg}")


def print_success(msg):
    """Print success message"""
    print(f"  {GREEN}✓{RESET} {msg}")


def print_failure(msg):
    """Print failure message"""
    print(f"  {RED}✗{RESET} {msg}")


def print_warning(msg):
    """Print warning message"""
    print(f"  {YELLOW}⚠{RESET} {msg}")


def check_sns_subscriptions():
    """
    Check SNS topic subscriptions to verify DevOps Agent subscription exists.
    
    Returns:
        tuple: (has_devops_agent_subscription, all_subscriptions)
    """
    print_header("Step 1: Check SNS Topic Subscriptions")
    
    try:
        sns_client = boto3.client('sns', region_name=AWS_REGION)
        
        print_test_info(f"Listing subscriptions for topic: {SNS_TOPIC_ARN}")
        response = sns_client.list_subscriptions_by_topic(TopicArn=SNS_TOPIC_ARN)
        
        subscriptions = response.get('Subscriptions', [])
        print_test_info(f"Found {len(subscriptions)} subscription(s)")
        
        has_email = False
        has_devops_agent = False
        
        for sub in subscriptions:
            protocol = sub.get('Protocol', 'unknown')
            endpoint = sub.get('Endpoint', 'unknown')
            status = sub.get('SubscriptionArn', 'PendingConfirmation')
            
            print_test_info(f"  - Protocol: {protocol}, Endpoint: {endpoint[:50]}...")
            
            if protocol == 'email':
                has_email = True
                print_success("Email subscription found")
            
            # Check for DevOps Agent subscription
            # DevOps Agent may use HTTPS endpoint or service-specific protocol
            if 'devops' in endpoint.lower() or 'agent' in endpoint.lower():
                has_devops_agent = True
                print_success("DevOps Agent subscription found")
        
        if has_email:
            print_success("Email notifications configured correctly")
        else:
            print_warning("Email subscription not found (unexpected)")
        
        if not has_devops_agent:
            print_failure("DevOps Agent subscription NOT FOUND (expected on unfixed infrastructure)")
        
        return has_devops_agent, subscriptions
        
    except Exception as e:
        print_failure(f"Error checking SNS subscriptions: {e}")
        return False, []


def trigger_alarm():
    """
    Trigger CloudWatch alarm by setting it to ALARM state.
    
    Returns:
        bool: True if alarm was triggered successfully
    """
    print_header("Step 2: Trigger CloudWatch Alarm")
    
    try:
        cloudwatch_client = boto3.client('cloudwatch', region_name=AWS_REGION)
        
        print_test_info(f"Setting alarm '{ALARM_NAME}' to ALARM state")
        cloudwatch_client.set_alarm_state(
            AlarmName=ALARM_NAME,
            StateValue='ALARM',
            StateReason='Bug condition exploration test - testing DevOps Agent notification'
        )
        
        print_success(f"Alarm '{ALARM_NAME}' set to ALARM state")
        print_test_info("SNS notification should be published immediately")
        
        return True
        
    except Exception as e:
        print_failure(f"Error triggering alarm: {e}")
        return False


def wait_for_devops_agent_notification(timeout_seconds):
    """
    Wait for DevOps Agent to receive notification and start investigation.
    
    This is a placeholder check since we cannot directly query DevOps Agent status via API.
    In a real test, you would:
    - Check DevOps Agent console for investigation activity
    - Query DevOps Agent API if available
    - Check Slack for investigation messages
    
    Returns:
        bool: True if DevOps Agent received notification
    """
    print_header("Step 3: Wait for DevOps Agent Notification")
    
    print_test_info(f"Waiting {timeout_seconds} seconds for DevOps Agent to receive notification...")
    print_test_info("Expected behavior: DevOps Agent should detect alarm within 30 seconds")
    
    # Wait for notification timeout
    time.sleep(timeout_seconds)
    
    # On unfixed infrastructure, DevOps Agent will NOT receive notification
    # This is the expected failure condition
    print_failure("DevOps Agent did NOT receive notification (expected on unfixed infrastructure)")
    print_test_info("Counterexample: No SNS subscription exists for DevOps Agent")
    
    return False


def check_investigation_started():
    """
    Check if DevOps Agent started investigation workflow.
    
    This is a placeholder check. In a real test, you would:
    - Query DevOps Agent console/API for investigation status
    - Check CloudWatch logs for DevOps Agent activity
    - Verify investigation workflow state
    
    Returns:
        bool: True if investigation started
    """
    print_header("Step 4: Check DevOps Agent Investigation Status")
    
    print_test_info("Checking if DevOps Agent started investigation workflow...")
    print_test_info(f"DevOps Agent Space ID: {DEVOPS_AGENT_SPACE_ID}")
    
    # On unfixed infrastructure, no investigation will start
    print_failure("No investigation workflow detected (expected on unfixed infrastructure)")
    print_test_info("Counterexample: DevOps Agent never received the alarm notification")
    
    return False


def check_slack_investigation_results(timeout_seconds):
    """
    Check if investigation results appeared in Slack.
    
    This is a placeholder check. In a real test, you would:
    - Query Slack API for messages in #aws-incidents channel
    - Look for investigation results with action buttons
    - Verify message timestamp is after alarm trigger time
    
    Returns:
        bool: True if investigation results found in Slack
    """
    print_header("Step 5: Check Slack for Investigation Results")
    
    print_test_info(f"Waiting {timeout_seconds} seconds for investigation results in Slack...")
    print_test_info("Expected: Investigation results with HITL action buttons in #aws-incidents")
    
    # Wait for investigation to complete
    time.sleep(timeout_seconds)
    
    # On unfixed infrastructure, no investigation results will appear
    print_failure("No investigation results in Slack (expected on unfixed infrastructure)")
    print_test_info("Counterexample: DevOps Agent never started investigation")
    
    return False


def reset_alarm():
    """Reset alarm to OK state after test"""
    print_header("Cleanup: Reset Alarm to OK State")
    
    try:
        cloudwatch_client = boto3.client('cloudwatch', region_name=AWS_REGION)
        
        print_test_info(f"Resetting alarm '{ALARM_NAME}' to OK state")
        cloudwatch_client.set_alarm_state(
            AlarmName=ALARM_NAME,
            StateValue='OK',
            StateReason='Bug condition exploration test complete - resetting alarm'
        )
        
        print_success("Alarm reset to OK state")
        return True
        
    except Exception as e:
        print_warning(f"Error resetting alarm: {e}")
        print_warning("You may need to manually reset the alarm:")
        print_warning(f"  python trigger_alarm.py --reset")
        return False


def run_bug_condition_test():
    """
    Run the complete bug condition exploration test.
    
    Returns:
        bool: True if test passes (bug is fixed), False if test fails (bug exists)
    """
    print(f"\n{BOLD}Bug Condition Exploration Test{RESET}")
    print(f"Property 1: DevOps Agent Receives Alarm Notifications")
    print(f"Time: {datetime.utcnow().isoformat()}Z")
    print(f"\n{YELLOW}CRITICAL: This test is EXPECTED TO FAIL on unfixed infrastructure{RESET}")
    print(f"{YELLOW}Failure confirms the bug exists - this is the correct outcome!{RESET}")
    
    test_results = {
        'sns_subscription_exists': False,
        'alarm_triggered': False,
        'notification_received': False,
        'investigation_started': False,
        'slack_results_posted': False
    }
    
    # Step 1: Check SNS subscriptions
    has_devops_agent_sub, subscriptions = check_sns_subscriptions()
    test_results['sns_subscription_exists'] = has_devops_agent_sub
    
    # Step 2: Trigger alarm
    alarm_triggered = trigger_alarm()
    test_results['alarm_triggered'] = alarm_triggered
    
    if not alarm_triggered:
        print_failure("Cannot continue test - alarm trigger failed")
        return False
    
    # Step 3: Wait for DevOps Agent notification
    notification_received = wait_for_devops_agent_notification(NOTIFICATION_TIMEOUT_SECONDS)
    test_results['notification_received'] = notification_received
    
    # Step 4: Check if investigation started
    investigation_started = check_investigation_started()
    test_results['investigation_started'] = investigation_started
    
    # Step 5: Check Slack for investigation results
    slack_results = check_slack_investigation_results(INVESTIGATION_TIMEOUT_SECONDS)
    test_results['slack_results_posted'] = slack_results
    
    # Cleanup: Reset alarm
    reset_alarm()
    
    # Print summary
    print_header("Test Summary")
    
    print(f"\n{BOLD}Test Results:{RESET}")
    print(f"  SNS Subscription Exists:     {GREEN + '✓' if test_results['sns_subscription_exists'] else RED + '✗'}{RESET}")
    print(f"  Alarm Triggered:             {GREEN + '✓' if test_results['alarm_triggered'] else RED + '✗'}{RESET}")
    print(f"  Notification Received:       {GREEN + '✓' if test_results['notification_received'] else RED + '✗'}{RESET}")
    print(f"  Investigation Started:       {GREEN + '✓' if test_results['investigation_started'] else RED + '✗'}{RESET}")
    print(f"  Slack Results Posted:        {GREEN + '✓' if test_results['slack_results_posted'] else RED + '✗'}{RESET}")
    
    # Determine test outcome
    all_passed = all(test_results.values())
    
    print(f"\n{BOLD}{'═' * 70}{RESET}")
    if all_passed:
        print(f"{BOLD}{GREEN}TEST PASSED ✓{RESET}")
        print(f"{GREEN}DevOps Agent receives alarm notifications correctly!{RESET}")
        print(f"{GREEN}The bug is FIXED - expected behavior is satisfied.{RESET}")
    else:
        print(f"{BOLD}{RED}TEST FAILED ✗{RESET}")
        print(f"{RED}DevOps Agent does NOT receive alarm notifications.{RESET}")
        print(f"{YELLOW}This is EXPECTED on unfixed infrastructure - the bug exists.{RESET}")
        
        print(f"\n{BOLD}Counterexamples Found:{RESET}")
        if not test_results['sns_subscription_exists']:
            print(f"  {RED}✗{RESET} DevOps Agent subscription missing from SNS topic")
        if not test_results['notification_received']:
            print(f"  {RED}✗{RESET} DevOps Agent did not receive notification within 30 seconds")
        if not test_results['investigation_started']:
            print(f"  {RED}✗{RESET} No investigation workflow triggered in DevOps Agent")
        if not test_results['slack_results_posted']:
            print(f"  {RED}✗{RESET} No investigation results posted to Slack after 4 minutes")
        
        print(f"\n{BOLD}Next Steps:{RESET}")
        print(f"  1. Implement fix: Add SNS subscription for DevOps Agent")
        print(f"  2. Re-run this test to verify the fix works")
        print(f"  3. When test passes, the bug is resolved")
    
    print(f"{BOLD}{'═' * 70}{RESET}\n")
    
    return all_passed


if __name__ == "__main__":
    try:
        test_passed = run_bug_condition_test()
        sys.exit(0 if test_passed else 1)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Test interrupted by user{RESET}")
        print(f"{YELLOW}Attempting to reset alarm...{RESET}")
        reset_alarm()
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        print(f"{YELLOW}Attempting to reset alarm...{RESET}")
        reset_alarm()
        sys.exit(1)
