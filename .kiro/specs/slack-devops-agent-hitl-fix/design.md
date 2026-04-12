# DevOps Agent Notification Subscription Bugfix Design

## Overview

The AWS DevOps Agent is not receiving CloudWatch alarm notifications because there is no SNS subscription connecting the alarm SNS topic to the DevOps Agent Space. While CloudWatch alarms correctly publish to the SNS topic (which forwards to email and AWS Chatbot for Slack), the DevOps Agent has no mechanism to receive these notifications and trigger its investigation workflow.

The fix requires adding an SNS subscription that connects the existing `autoops-alarms-dev` SNS topic to the DevOps Agent Space's notification endpoint. This will enable the Agent to receive alarm state change events and automatically initiate its HITL investigation workflow.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when CloudWatch alarms fire but the DevOps Agent does not receive the notification
- **Property (P)**: The desired behavior when alarms fire - DevOps Agent receives the notification within 30 seconds and starts investigation
- **Preservation**: Existing email and Slack (AWS Chatbot) notifications that must continue working unchanged
- **SNS Topic**: `autoops-alarms-dev` - the SNS topic that receives CloudWatch alarm notifications
- **DevOps Agent Space**: The AWS managed service instance that performs autonomous incident investigation
- **HITL Workflow**: Human-in-the-Loop workflow where the Agent investigates and posts action buttons to Slack
- **Alarm State Change Event**: CloudWatch alarm transitioning from OK → ALARM or ALARM → OK

## Bug Details

### Fault Condition

The bug manifests when a CloudWatch alarm transitions to ALARM state and publishes to the SNS topic, but the DevOps Agent Space does not receive the notification. The SNS topic has subscriptions for email and AWS Chatbot (Slack), but is missing a subscription for the DevOps Agent notification endpoint.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type CloudWatchAlarmStateChange
  OUTPUT: boolean
  
  RETURN input.alarmState == "ALARM"
         AND input.publishedToSNS == true
         AND devopsAgentSubscriptionExists(snsTopicArn) == false
         AND devopsAgentReceivedNotification(input.alarmName) == false
END FUNCTION
```

### Examples

- **Example 1**: User runs `python trigger_alarm.py` → CloudWatch alarm `autoops-lambda-errors-dev` transitions to ALARM → SNS topic receives notification → Email sent ✓, Slack message posted ✓, DevOps Agent investigation starts ✗
- **Example 2**: DynamoDB write throttle occurs → CloudWatch alarm `autoops-dynamodb-write-throttles-dev` fires → SNS notification sent → Email received ✓, Slack alert appears ✓, DevOps Agent HITL workflow triggers ✗
- **Example 3**: Lambda function experiences high error rate → CloudWatch alarm fires → User waits 4 minutes → Email notification received ✓, Slack shows alarm ✓, No investigation results in Slack ✗
- **Edge Case**: Alarm transitions to OK state → SNS notification sent → Email and Slack show OK status ✓, DevOps Agent should also receive OK notification but doesn't ✗

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Email notifications via SNS subscription must continue to work exactly as before
- AWS Chatbot Slack notifications to #aws-incidents channel must continue to work exactly as before
- CloudWatch alarm triggering logic and thresholds must remain unchanged
- SNS topic policy allowing CloudWatch to publish must remain unchanged
- All existing alarm actions and OK actions must remain unchanged

**Scope:**
All inputs that do NOT involve the DevOps Agent notification mechanism should be completely unaffected by this fix. This includes:
- Email delivery via SNS
- Slack message delivery via AWS Chatbot
- CloudWatch alarm evaluation and state transitions
- SNS topic policy and permissions
- Other SNS subscriptions (email, future subscriptions)

## Hypothesized Root Cause

Based on the bug description and infrastructure analysis, the root cause is:

1. **Missing SNS Subscription**: The SNS topic `autoops-alarms-dev` has two subscriptions (email and implicitly AWS Chatbot via console setup), but lacks a subscription for the DevOps Agent Space notification endpoint
   - The DevOps Agent console allows "connecting alarms" but this only grants read permissions
   - Connecting alarms does NOT create an SNS subscription for state change notifications
   - The Agent needs an active push notification mechanism, not just read access

2. **DevOps Agent Notification Endpoint Unknown**: AWS DevOps Agent Spaces have notification endpoints that can receive SNS messages, but these endpoints are not exposed in Terraform or easily discoverable
   - The endpoint format may be service-managed and region-specific
   - The endpoint may require specific IAM permissions in the SNS topic policy

3. **Manual Console Configuration Gap**: The documentation in `docs/04-devops-agent-setup.md` describes connecting alarms in the DevOps Agent console, but this connection is for read access only
   - Users may assume "connecting alarms" means the Agent will receive notifications
   - The actual notification subscription must be configured separately

4. **Terraform Resource Limitation**: The `devops_agent.tf` file uses `null_resource` with manual instructions because AWS DevOps Agent lacks native Terraform support
   - This prevents automated SNS subscription creation during `terraform apply`
   - The SNS subscription must be created manually or via AWS CLI

## Correctness Properties

Property 1: Fault Condition - DevOps Agent Receives Alarm Notifications

_For any_ CloudWatch alarm state change event where the alarm transitions to ALARM state and publishes to the SNS topic, the fixed infrastructure SHALL deliver the notification to the DevOps Agent Space within 30 seconds, causing the Agent to initiate its investigation workflow and post results to Slack within 2-4 minutes.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

Property 2: Preservation - Existing Notification Channels

_For any_ CloudWatch alarm state change event (ALARM or OK), the fixed infrastructure SHALL continue to deliver notifications via email and AWS Chatbot to Slack exactly as before, preserving all existing notification behavior for non-DevOps-Agent channels.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct (missing SNS subscription):

**File**: `terraform/sns.tf`

**Resource**: Add new SNS topic subscription for DevOps Agent

**Specific Changes**:
1. **Research DevOps Agent Notification Endpoint**: Determine the correct endpoint format for DevOps Agent Spaces
   - Check AWS documentation for DevOps Agent SNS integration
   - Identify if endpoint is service-managed or user-provided
   - Determine if endpoint requires specific protocol (HTTPS, Lambda, etc.)

2. **Add SNS Topic Policy Statement**: Update `aws_sns_topic_policy.alarms` to allow DevOps Agent service principal to subscribe
   - Add permission for `devops-agent.amazonaws.com` to subscribe to the topic
   - Ensure policy allows SNS message delivery to DevOps Agent endpoints

3. **Create SNS Subscription Resource**: Add `aws_sns_topic_subscription.devops_agent` resource
   - Protocol: Likely `https` or service-specific protocol
   - Endpoint: DevOps Agent Space notification endpoint (may need to be parameterized)
   - Filter policy: Optional - could filter for ALARM state only

4. **Add Terraform Variable**: Add `devops_agent_notification_endpoint` variable to `variables.tf`
   - Type: string
   - Description: DevOps Agent Space notification endpoint URL
   - Default: Empty string (user must provide after creating Agent Space)

5. **Update Documentation**: Modify `docs/04-devops-agent-setup.md` to include SNS subscription setup
   - Add step to retrieve DevOps Agent notification endpoint from console
   - Add step to run `terraform apply` again after obtaining endpoint
   - Clarify that "connecting alarms" in console is for read access only

**Alternative Approach (if endpoint is not available in Terraform)**:
If the DevOps Agent notification endpoint cannot be obtained programmatically:

1. **Use AWS CLI in null_resource**: Add a `null_resource` that uses AWS CLI to create the SNS subscription after Agent Space creation
2. **Manual Console Step**: Document manual SNS subscription creation in AWS Console
3. **EventBridge Alternative**: Investigate using EventBridge rules to forward CloudWatch alarm events to DevOps Agent instead of SNS

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed infrastructure, then verify the fix works correctly and preserves existing notification behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that the DevOps Agent does not receive notifications when alarms fire.

**Test Plan**: Trigger CloudWatch alarms using `trigger_alarm.py` and observe notification delivery to all channels. Run these tests on the UNFIXED infrastructure to confirm the Agent does not receive notifications.

**Test Cases**:
1. **Lambda Error Alarm Test**: Run `trigger_alarm.py` to set `autoops-lambda-errors-dev` to ALARM state → Observe email received ✓, Slack message posted ✓, DevOps Agent investigation starts ✗ (will fail on unfixed infrastructure)
2. **DynamoDB Throttle Test**: Run `trigger_throttle.py` to cause real DynamoDB throttle → Observe alarm fires → Email received ✓, Slack alert ✓, DevOps Agent HITL workflow ✗ (will fail on unfixed infrastructure)
3. **SNS Subscription Check**: Run `aws sns list-subscriptions-by-topic --topic-arn <topic-arn>` → Observe only email subscription exists, no DevOps Agent subscription (will fail on unfixed infrastructure)
4. **DevOps Agent Console Check**: Check DevOps Agent Space console → Observe "6 alarms connected" but no recent investigation activity (will fail on unfixed infrastructure)

**Expected Counterexamples**:
- DevOps Agent does not initiate investigation workflows when alarms fire
- SNS topic has only 1-2 subscriptions (email, possibly implicit Chatbot), missing DevOps Agent subscription
- Possible causes: missing SNS subscription, incorrect endpoint configuration, missing IAM permissions

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (alarm fires), the fixed infrastructure delivers notifications to the DevOps Agent and triggers investigation.

**Pseudocode:**
```
FOR ALL alarmStateChange WHERE isBugCondition(alarmStateChange) DO
  result := triggerAlarmAndWait(alarmStateChange)
  ASSERT devopsAgentReceivedNotification(result) == true
  ASSERT devopsAgentStartedInvestigation(result) == true
  ASSERT slackContainsInvestigationResults(result) == true
END FOR
```

**Test Plan**: After implementing the fix, trigger alarms and verify DevOps Agent receives notifications and performs investigations.

**Test Cases**:
1. **SNS Subscription Verification**: Run `aws sns list-subscriptions-by-topic --topic-arn <topic-arn>` → Verify DevOps Agent subscription exists with correct endpoint and protocol
2. **Lambda Error Alarm Test (Fixed)**: Trigger `autoops-lambda-errors-dev` alarm → Wait 30 seconds → Verify DevOps Agent shows "Investigation started" in console → Wait 4 minutes → Verify investigation results appear in Slack
3. **DynamoDB Throttle Test (Fixed)**: Run `trigger_throttle.py` → Wait for alarm → Verify DevOps Agent investigation workflow completes → Verify Slack shows investigation with action buttons
4. **Multiple Alarm Test**: Trigger multiple alarms in sequence → Verify DevOps Agent handles each alarm independently and posts separate investigations

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (existing notification channels), the fixed infrastructure produces the same result as the original infrastructure.

**Pseudocode:**
```
FOR ALL alarmStateChange WHERE NOT isBugCondition(alarmStateChange) DO
  ASSERT emailNotificationSent(alarmStateChange) == true
  ASSERT slackChatbotMessagePosted(alarmStateChange) == true
  ASSERT alarmStateTransitionCorrect(alarmStateChange) == true
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across different alarm types
- It catches edge cases like OK state transitions, insufficient data states
- It provides strong guarantees that existing notification behavior is unchanged

**Test Plan**: Observe behavior on UNFIXED infrastructure first for email and Slack notifications, then write tests capturing that behavior and verify it continues after fix.

**Test Cases**:
1. **Email Notification Preservation**: Trigger alarm → Verify email received with same format, timing, and content as before fix
2. **Slack Chatbot Preservation**: Trigger alarm → Verify AWS Chatbot posts message to #aws-incidents with same format as before fix
3. **OK State Notification Preservation**: Transition alarm from ALARM → OK → Verify email and Slack receive OK notifications as before
4. **SNS Topic Policy Preservation**: Verify CloudWatch can still publish to SNS topic (no permission errors in CloudWatch logs)
5. **Multiple Subscription Delivery**: Verify adding DevOps Agent subscription does not interfere with email or Chatbot delivery timing

### Unit Tests

- Test SNS topic policy allows DevOps Agent service principal to subscribe
- Test SNS subscription is created with correct protocol and endpoint
- Test alarm state changes publish to SNS topic successfully
- Test DevOps Agent IAM role has permissions to receive SNS notifications (if required)

### Property-Based Tests

- Generate random alarm state transitions (OK → ALARM, ALARM → OK, ALARM → INSUFFICIENT_DATA) and verify all notification channels receive messages
- Generate random alarm configurations and verify DevOps Agent subscription works for all alarm types
- Test that concurrent alarm firings are handled correctly by all notification channels

### Integration Tests

- Test full incident flow: alarm fires → email sent → Slack notified → DevOps Agent investigates → investigation posted to Slack
- Test alarm lifecycle: ALARM → investigation → manual remediation → OK → all channels notified
- Test that DevOps Agent investigation results include correct alarm context and resource information
