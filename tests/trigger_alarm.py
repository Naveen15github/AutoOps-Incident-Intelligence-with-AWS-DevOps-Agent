#!/usr/bin/env python3
"""
Trigger CloudWatch Alarm for Testing DevOps Agent

This script manually sets a CloudWatch alarm to ALARM state
to test the DevOps Agent + Slack integration.

Usage:
    python trigger_alarm.py           # Set alarm to ALARM
    python trigger_alarm.py --reset   # Reset alarm to OK
"""

import boto3
import sys

def set_alarm_state(alarm_name, state, reason):
    """
    Manually set CloudWatch alarm state
    
    Args:
        alarm_name: Name of the alarm
        state: 'ALARM' or 'OK'
        reason: Reason for state change
    """
    try:
        client = boto3.client('cloudwatch', region_name='us-east-1')
        
        response = client.set_alarm_state(
            AlarmName=alarm_name,
            StateValue=state,
            StateReason=reason
        )
        
        print("═" * 60)
        print(f"✅ Successfully set alarm '{alarm_name}' to {state}")
        print(f"   Reason: {reason}")
        print("═" * 60)
        
        if state == 'ALARM':
            print("\n⏳ What happens next:")
            print("   1. SNS sends email notification (immediate)")
            print("   2. DevOps Agent detects alarm (~30 seconds)")
            print("   3. DevOps Agent investigates (~2-4 minutes)")
            print("   4. Investigation results posted to Slack")
            print("\n📱 Check your Slack #aws-incidents channel in 2-3 minutes")
            print("\n💡 To reset the alarm after testing:")
            print("   python trigger_alarm.py --reset")
        else:
            print("\n✅ Alarm reset to OK state")
            print("   Test complete!")
        
        print("═" * 60)
        return True
        
    except Exception as e:
        print("═" * 60)
        print(f"❌ Error: {e}")
        print("═" * 60)
        print("\nTroubleshooting:")
        print("  1. Make sure AWS credentials are configured:")
        print("     aws configure")
        print("  2. Verify you have permissions to modify CloudWatch alarms")
        print("  3. Check that the alarm exists:")
        print(f"     aws cloudwatch describe-alarms --alarm-names {alarm_name}")
        print("═" * 60)
        return False

if __name__ == "__main__":
    alarm_name = "autoops-lambda-errors-dev"
    
    if "--reset" in sys.argv or "--ok" in sys.argv:
        state = "OK"
        reason = "Test complete - resetting alarm"
    else:
        state = "ALARM"
        reason = "Testing DevOps Agent Slack integration"
    
    set_alarm_state(alarm_name, state, reason)
