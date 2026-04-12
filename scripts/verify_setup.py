#!/usr/bin/env python3
"""
Verification script to check if DevOps Agent setup is complete.

This script checks:
1. IAM role exists and has correct trust policy
2. Policy is attached to the role
3. Terraform resources are accessible
4. (Optional) DevOps Agent Space exists

Usage:
    python scripts/verify_setup.py --region us-east-1 --environment dev
"""

import argparse
import json
import subprocess
import sys

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("❌ Error: boto3 is not installed. Run: pip install boto3")
    sys.exit(1)


class SetupVerifier:
    """Verifies DevOps Agent setup is complete."""

    def __init__(self, region: str, environment: str, project_name: str = "autoops"):
        self.region = region
        self.environment = environment
        self.project_name = project_name
        
        self.iam_client = boto3.client('iam', region_name=region)
        self.ssm_client = boto3.client('ssm', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        self.account_id = self.sts_client.get_caller_identity()['Account']
        self.role_name = f"{project_name}-devops-agent-role-{environment}"
        self.policy_name = f"{project_name}-devops-agent-observe-policy-{environment}"
        
        self.checks_passed = 0
        self.checks_failed = 0

    def print_header(self, message: str):
        """Print a formatted header."""
        print(f"\n{'='*70}")
        print(f"  {message}")
        print(f"{'='*70}\n")

    def check_iam_role(self) -> bool:
        """Check if IAM role exists and has correct trust policy."""
        print("🔍 Checking IAM role...")
        
        try:
            response = self.iam_client.get_role(RoleName=self.role_name)
            role = response['Role']
            
            # Check trust policy
            trust_policy = json.loads(
                response['Role']['AssumeRolePolicyDocument']
                if isinstance(response['Role']['AssumeRolePolicyDocument'], str)
                else json.dumps(response['Role']['AssumeRolePolicyDocument'])
            )
            
            has_correct_principal = False
            for statement in trust_policy.get('Statement', []):
                service = statement.get('Principal', {}).get('Service', '')
                if service == 'devops-agent.amazonaws.com':
                    has_correct_principal = True
                    break
            
            if has_correct_principal:
                print(f"✅ IAM role exists: {role['Arn']}")
                print(f"✅ Trust policy is correct (devops-agent.amazonaws.com)")
                self.checks_passed += 2
                return True
            else:
                print(f"⚠️  IAM role exists but trust policy is incorrect")
                print(f"   Expected service principal: devops-agent.amazonaws.com")
                self.checks_passed += 1
                self.checks_failed += 1
                return False
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                print(f"❌ IAM role not found: {self.role_name}")
                print(f"   Run: python scripts/setup_devops_agent.py --region {self.region}")
            else:
                print(f"❌ Error checking IAM role: {e}")
            self.checks_failed += 2
            return False

    def check_policy_attachment(self) -> bool:
        """Check if policy is attached to the role."""
        print("\n🔍 Checking policy attachment...")
        
        policy_arn = f"arn:aws:iam::{self.account_id}:policy/{self.policy_name}"
        
        try:
            response = self.iam_client.list_attached_role_policies(RoleName=self.role_name)
            attached_policies = [p['PolicyArn'] for p in response['AttachedPolicies']]
            
            if policy_arn in attached_policies:
                print(f"✅ Policy is attached: {self.policy_name}")
                self.checks_passed += 1
                return True
            else:
                print(f"❌ Policy not attached: {self.policy_name}")
                print(f"   Expected: {policy_arn}")
                self.checks_failed += 1
                return False
                
        except ClientError as e:
            print(f"❌ Error checking policy attachment: {e}")
            self.checks_failed += 1
            return False

    def check_terraform_outputs(self) -> bool:
        """Check if Terraform outputs are accessible."""
        print("\n🔍 Checking Terraform outputs...")
        
        checks = {
            'DynamoDB table': f"/{self.project_name}/{self.environment}/dynamodb-table-name",
            'API endpoint': f"/{self.project_name}/{self.environment}/api-endpoint",
            'Alarm ARNs': f"/{self.project_name}/{self.environment}/alarm-arns"
        }
        
        all_found = True
        for name, param_name in checks.items():
            try:
                response = self.ssm_client.get_parameter(Name=param_name)
                value = response['Parameter']['Value']
                if name == 'Alarm ARNs':
                    alarm_count = len(value.split(','))
                    print(f"✅ {name}: {alarm_count} alarms found")
                else:
                    print(f"✅ {name}: {value[:50]}...")
                self.checks_passed += 1
            except ClientError:
                print(f"❌ {name} not found in SSM: {param_name}")
                print(f"   Run: cd terraform && terraform apply")
                self.checks_failed += 1
                all_found = False
        
        return all_found

    def check_devops_agent_space(self) -> bool:
        """Check if DevOps Agent Space exists (optional)."""
        print("\n🔍 Checking DevOps Agent Space...")
        
        try:
            result = subprocess.run(
                ['aws', 'devops-agent', 'list-spaces', '--region', self.region, '--output', 'json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"⚠️  Cannot check DevOps Agent Space (AWS CLI may not support it)")
                print(f"   This is optional - you can create it manually in the Console")
                return True  # Don't count as failure
            
            spaces = json.loads(result.stdout)
            space_name = f"{self.project_name}-incident-intelligence"
            
            existing_space = next(
                (s for s in spaces.get('spaces', []) if s.get('spaceName') == space_name),
                None
            )
            
            if existing_space:
                print(f"✅ DevOps Agent Space exists: {space_name}")
                print(f"   Space ID: {existing_space.get('spaceId')}")
                self.checks_passed += 1
                return True
            else:
                print(f"⚠️  DevOps Agent Space not found: {space_name}")
                print(f"   Run: python scripts/setup_devops_agent.py --region {self.region}")
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            print(f"⚠️  Cannot check DevOps Agent Space (AWS CLI may not support it)")
            print(f"   This is optional - you can create it manually in the Console")
            return True  # Don't count as failure

    def print_summary(self):
        """Print verification summary."""
        self.print_header("VERIFICATION SUMMARY")
        
        total_checks = self.checks_passed + self.checks_failed
        print(f"Total checks: {total_checks}")
        print(f"✅ Passed: {self.checks_passed}")
        print(f"❌ Failed: {self.checks_failed}")
        
        if self.checks_failed == 0:
            print(f"\n🎉 All checks passed! Your setup is complete.")
            print(f"\nNext steps:")
            print(f"1. Set up Slack integration (see scripts/QUICKSTART.md)")
            print(f"2. Test your API: cd tests && python test_api.py")
            print(f"3. Trigger an incident: python tests/trigger_throttle.py")
        else:
            print(f"\n⚠️  Some checks failed. Please review the errors above.")
            print(f"\nTo fix:")
            print(f"1. Run: python scripts/setup_devops_agent.py --region {self.region}")
            print(f"2. Ensure Terraform is applied: cd terraform && terraform apply")

    def run(self):
        """Run all verification checks."""
        self.print_header(f"DevOps Agent Setup Verification - {self.environment.upper()}")
        
        print(f"Region: {self.region}")
        print(f"Environment: {self.environment}")
        print(f"Project: {self.project_name}")
        print(f"Account ID: {self.account_id}")
        
        # Run checks
        self.check_iam_role()
        self.check_policy_attachment()
        self.check_terraform_outputs()
        self.check_devops_agent_space()
        
        # Print summary
        self.print_summary()
        
        # Exit with appropriate code
        sys.exit(0 if self.checks_failed == 0 else 1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Verify AWS DevOps Agent setup is complete'
    )
    
    parser.add_argument(
        '--region',
        required=True,
        help='AWS region (e.g., us-east-1)'
    )
    
    parser.add_argument(
        '--environment',
        default='dev',
        help='Environment name (default: dev)'
    )
    
    parser.add_argument(
        '--project',
        default='autoops',
        help='Project name (default: autoops)'
    )
    
    args = parser.parse_args()
    
    verifier = SetupVerifier(
        region=args.region,
        environment=args.environment,
        project_name=args.project
    )
    verifier.run()


if __name__ == '__main__':
    main()
