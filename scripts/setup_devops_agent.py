#!/usr/bin/env python3
"""
AWS DevOps Agent Setup Automation Script

This script automates the creation of an AWS DevOps Agent Space for monitoring
the AutoOps serverless API infrastructure.

Prerequisites:
- AWS CLI installed and configured
- boto3 installed (pip install boto3)
- Terraform infrastructure already deployed
- AWS DevOps Agent service available in your region

Usage:
    python scripts/setup_devops_agent.py --region us-east-1 --environment dev
"""

import argparse
import json
import subprocess
import sys
import time
from typing import Dict, List, Optional

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("❌ Error: boto3 is not installed. Run: pip install boto3")
    sys.exit(1)


class DevOpsAgentSetup:
    """Handles AWS DevOps Agent Space creation and configuration."""

    def __init__(self, region: str, environment: str, project_name: str = "autoops"):
        self.region = region
        self.environment = environment
        self.project_name = project_name
        
        # Initialize AWS clients
        self.iam_client = boto3.client('iam', region_name=region)
        self.ssm_client = boto3.client('ssm', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get account ID
        self.account_id = self.sts_client.get_caller_identity()['Account']
        
        # Resource names
        self.role_name = f"{project_name}-devops-agent-role-{environment}"
        self.policy_name = f"{project_name}-devops-agent-observe-policy-{environment}"
        self.space_name = f"{project_name}-incident-intelligence"

    def print_header(self, message: str):
        """Print a formatted header."""
        print(f"\n{'='*70}")
        print(f"  {message}")
        print(f"{'='*70}\n")

    def print_step(self, step: int, message: str):
        """Print a step message."""
        print(f"📋 Step {step}: {message}")

    def print_success(self, message: str):
        """Print a success message."""
        print(f"✅ {message}")

    def print_info(self, message: str):
        """Print an info message."""
        print(f"ℹ️  {message}")

    def print_error(self, message: str):
        """Print an error message."""
        print(f"❌ {message}")

    def create_iam_role(self) -> str:
        """Create IAM role for DevOps Agent with trust policy."""
        self.print_step(1, "Creating IAM Role for DevOps Agent")
        
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "devops-agent.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            # Check if role already exists
            try:
                response = self.iam_client.get_role(RoleName=self.role_name)
                role_arn = response['Role']['Arn']
                self.print_info(f"Role already exists: {role_arn}")
                return role_arn
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchEntity':
                    raise
            
            # Create the role
            response = self.iam_client.create_role(
                RoleName=self.role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Role assumed by AWS DevOps Agent to observe AutoOps infrastructure"
            )
            role_arn = response['Role']['Arn']
            self.print_success(f"Created IAM role: {role_arn}")
            
            # Wait for role to be available
            time.sleep(5)
            
            return role_arn
            
        except ClientError as e:
            self.print_error(f"Failed to create IAM role: {e}")
            raise

    def attach_policy_to_role(self):
        """Attach the observability policy to the DevOps Agent role."""
        self.print_step(2, "Attaching observability policy to role")
        
        policy_arn = f"arn:aws:iam::{self.account_id}:policy/{self.policy_name}"
        
        try:
            # Check if policy is already attached
            response = self.iam_client.list_attached_role_policies(RoleName=self.role_name)
            attached_policies = [p['PolicyArn'] for p in response['AttachedPolicies']]
            
            if policy_arn in attached_policies:
                self.print_info(f"Policy already attached: {policy_arn}")
                return
            
            # Attach the policy
            self.iam_client.attach_role_policy(
                RoleName=self.role_name,
                PolicyArn=policy_arn
            )
            self.print_success(f"Attached policy: {policy_arn}")
            
        except ClientError as e:
            self.print_error(f"Failed to attach policy: {e}")
            raise

    def get_terraform_outputs(self) -> Dict[str, str]:
        """Retrieve resource information from SSM parameters (Terraform outputs)."""
        self.print_step(3, "Retrieving resource information from Terraform outputs")
        
        resources = {}
        
        try:
            # Get Lambda function name
            param_name = f"/{self.project_name}/{self.environment}/lambda-function-name"
            try:
                response = self.ssm_client.get_parameter(Name=param_name)
                resources['lambda_name'] = response['Parameter']['Value']
                self.print_info(f"Lambda function: {resources['lambda_name']}")
            except ClientError:
                # Fallback: construct from naming convention
                resources['lambda_name'] = f"{self.project_name}-api-{self.environment}"
                self.print_info(f"Lambda function (fallback): {resources['lambda_name']}")
            
            # Get DynamoDB table name
            param_name = f"/{self.project_name}/{self.environment}/dynamodb-table-name"
            response = self.ssm_client.get_parameter(Name=param_name)
            resources['dynamodb_table'] = response['Parameter']['Value']
            self.print_info(f"DynamoDB table: {resources['dynamodb_table']}")
            
            # Get CloudWatch alarm ARNs
            param_name = f"/{self.project_name}/{self.environment}/alarm-arns"
            response = self.ssm_client.get_parameter(Name=param_name)
            resources['alarm_arns'] = response['Parameter']['Value'].split(',')
            self.print_info(f"CloudWatch alarms: {len(resources['alarm_arns'])} alarms found")
            
            # Get API Gateway ID from endpoint
            param_name = f"/{self.project_name}/{self.environment}/api-endpoint"
            response = self.ssm_client.get_parameter(Name=param_name)
            api_endpoint = response['Parameter']['Value']
            # Extract API ID from URL: https://{api-id}.execute-api.{region}.amazonaws.com/{stage}
            api_id = api_endpoint.split('//')[1].split('.')[0]
            resources['api_gateway_id'] = api_id
            self.print_info(f"API Gateway ID: {resources['api_gateway_id']}")
            
            return resources
            
        except ClientError as e:
            self.print_error(f"Failed to retrieve Terraform outputs: {e}")
            self.print_info("Make sure Terraform has been applied successfully")
            raise

    def check_devops_agent_cli(self) -> bool:
        """Check if AWS CLI supports devops-agent commands."""
        try:
            result = subprocess.run(
                ['aws', 'devops-agent', 'help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def create_agent_space(self, role_arn: str, resources: Dict[str, str]):
        """Create DevOps Agent Space using AWS CLI."""
        self.print_step(4, "Creating DevOps Agent Space")
        
        # Check if AWS CLI supports devops-agent
        if not self.check_devops_agent_cli():
            self.print_error("AWS CLI does not support 'devops-agent' commands")
            self.print_info("This might mean:")
            self.print_info("  1. AWS CLI version is too old (update with: pip install --upgrade awscli)")
            self.print_info("  2. DevOps Agent service is not available in your region")
            self.print_info("  3. You need to use the AWS Console instead")
            self.print_manual_instructions(role_arn, resources)
            return False
        
        # Prepare the create-space command
        space_config = {
            'spaceName': self.space_name,
            'description': f'Monitors the {self.project_name} serverless API for incidents and performance issues',
            'roleArn': role_arn
        }
        
        try:
            # Check if space already exists
            list_cmd = [
                'aws', 'devops-agent', 'list-spaces',
                '--region', self.region,
                '--output', 'json'
            ]
            
            result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                spaces = json.loads(result.stdout)
                existing_space = next(
                    (s for s in spaces.get('spaces', []) if s.get('spaceName') == self.space_name),
                    None
                )
                if existing_space:
                    self.print_info(f"Agent Space already exists: {self.space_name}")
                    space_id = existing_space.get('spaceId')
                    self.print_success(f"Space ID: {space_id}")
                    return True
            
            # Create the space
            create_cmd = [
                'aws', 'devops-agent', 'create-space',
                '--space-name', space_config['spaceName'],
                '--description', space_config['description'],
                '--role-arn', space_config['roleArn'],
                '--region', self.region,
                '--output', 'json'
            ]
            
            self.print_info(f"Creating space: {self.space_name}")
            result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                self.print_error(f"Failed to create space: {result.stderr}")
                self.print_manual_instructions(role_arn, resources)
                return False
            
            response = json.loads(result.stdout)
            space_id = response.get('spaceId')
            self.print_success(f"Created Agent Space: {self.space_name}")
            self.print_success(f"Space ID: {space_id}")
            
            # Connect resources
            self.connect_resources(space_id, resources)
            
            return True
            
        except subprocess.TimeoutExpired:
            self.print_error("Command timed out")
            self.print_manual_instructions(role_arn, resources)
            return False
        except Exception as e:
            self.print_error(f"Failed to create Agent Space: {e}")
            self.print_manual_instructions(role_arn, resources)
            return False

    def connect_resources(self, space_id: str, resources: Dict[str, str]):
        """Connect CloudWatch logs, alarms, and AWS resources to the Agent Space."""
        self.print_step(5, "Connecting resources to Agent Space")
        
        try:
            # Connect CloudWatch log groups
            log_groups = [
                f"/aws/lambda/{resources['lambda_name']}",
                f"/aws/apigateway/{self.project_name}-{self.environment}"
            ]
            
            for log_group in log_groups:
                cmd = [
                    'aws', 'devops-agent', 'connect-log-group',
                    '--space-id', space_id,
                    '--log-group-name', log_group,
                    '--region', self.region
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    self.print_success(f"Connected log group: {log_group}")
                else:
                    self.print_info(f"Skipped log group (may not exist): {log_group}")
            
            # Connect CloudWatch alarms
            for alarm_arn in resources['alarm_arns']:
                cmd = [
                    'aws', 'devops-agent', 'connect-alarm',
                    '--space-id', space_id,
                    '--alarm-arn', alarm_arn.strip(),
                    '--region', self.region
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    alarm_name = alarm_arn.split(':')[-1]
                    self.print_success(f"Connected alarm: {alarm_name}")
            
            # Connect Lambda function
            lambda_arn = f"arn:aws:lambda:{self.region}:{self.account_id}:function:{resources['lambda_name']}"
            cmd = [
                'aws', 'devops-agent', 'connect-resource',
                '--space-id', space_id,
                '--resource-arn', lambda_arn,
                '--region', self.region
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.print_success(f"Connected Lambda: {resources['lambda_name']}")
            
            # Connect DynamoDB table
            dynamodb_arn = f"arn:aws:dynamodb:{self.region}:{self.account_id}:table/{resources['dynamodb_table']}"
            cmd = [
                'aws', 'devops-agent', 'connect-resource',
                '--space-id', space_id,
                '--resource-arn', dynamodb_arn,
                '--region', self.region
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.print_success(f"Connected DynamoDB: {resources['dynamodb_table']}")
            
            # Connect API Gateway
            api_arn = f"arn:aws:apigateway:{self.region}::/restapis/{resources['api_gateway_id']}"
            cmd = [
                'aws', 'devops-agent', 'connect-resource',
                '--space-id', space_id,
                '--resource-arn', api_arn,
                '--region', self.region
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.print_success(f"Connected API Gateway: {resources['api_gateway_id']}")
            
            # Enable X-Ray tracing
            cmd = [
                'aws', 'devops-agent', 'update-space',
                '--space-id', space_id,
                '--enable-xray',
                '--region', self.region
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.print_success("Enabled X-Ray tracing")
            
        except Exception as e:
            self.print_error(f"Failed to connect some resources: {e}")
            self.print_info("You can manually connect resources in the AWS Console")

    def print_manual_instructions(self, role_arn: str, resources: Dict[str, str]):
        """Print manual setup instructions for the AWS Console."""
        self.print_header("MANUAL SETUP REQUIRED")
        
        print("Please complete the setup manually in the AWS Console:")
        print(f"\n1. Go to: https://console.aws.amazon.com/devops-agent")
        print(f"\n2. Click 'Create Agent Space'")
        print(f"\n3. Configure the space:")
        print(f"   - Space name: {self.space_name}")
        print(f"   - Description: Monitors the {self.project_name} serverless API")
        print(f"   - IAM role ARN: {role_arn}")
        print(f"\n4. Connect CloudWatch log groups:")
        print(f"   - /aws/lambda/{resources['lambda_name']}")
        print(f"   - /aws/apigateway/{self.project_name}-{self.environment}")
        print(f"\n5. Connect all CloudWatch alarms (6 alarms):")
        for i, arn in enumerate(resources['alarm_arns'], 1):
            alarm_name = arn.split(':')[-1]
            print(f"   {i}. {alarm_name}")
        print(f"\n6. Connect AWS resources:")
        print(f"   - Lambda: {resources['lambda_name']}")
        print(f"   - DynamoDB: {resources['dynamodb_table']}")
        print(f"   - API Gateway: {resources['api_gateway_id']}")
        print(f"\n7. Enable X-Ray tracing")

    def print_slack_instructions(self):
        """Print instructions for Slack integration."""
        self.print_header("NEXT STEP: SLACK INTEGRATION")
        
        print("AWS DevOps Agent Space is ready! Now set up Slack notifications:")
        print(f"\n1. Open the AWS Console:")
        print(f"   https://console.aws.amazon.com/devops-agent")
        print(f"\n2. Select your space: {self.space_name}")
        print(f"\n3. Go to 'Notifications' tab")
        print(f"\n4. Click 'Configure Slack'")
        print(f"\n5. Follow the guided setup to:")
        print(f"   - Authorize AWS Chatbot with your Slack workspace")
        print(f"   - Select the channel for notifications")
        print(f"   - Configure notification preferences")
        print(f"\n6. Test the integration:")
        print(f"   cd tests && python trigger_throttle.py")
        print(f"\nFor detailed instructions, see: docs/03-slack-setup.md")

    def run(self):
        """Execute the complete setup process."""
        self.print_header(f"AWS DevOps Agent Setup - {self.environment.upper()}")
        
        print(f"Region: {self.region}")
        print(f"Environment: {self.environment}")
        print(f"Project: {self.project_name}")
        print(f"Account ID: {self.account_id}")
        
        try:
            # Step 1: Create IAM role
            role_arn = self.create_iam_role()
            
            # Step 2: Attach policy
            self.attach_policy_to_role()
            
            # Step 3: Get Terraform outputs
            resources = self.get_terraform_outputs()
            
            # Step 4 & 5: Create space and connect resources
            success = self.create_agent_space(role_arn, resources)
            
            # Print next steps
            if success:
                self.print_slack_instructions()
            
            self.print_header("SETUP COMPLETE")
            self.print_success("DevOps Agent IAM role is ready")
            if success:
                self.print_success("DevOps Agent Space is configured")
            else:
                self.print_info("Complete the Agent Space setup manually (see instructions above)")
            
        except Exception as e:
            self.print_error(f"Setup failed: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Automate AWS DevOps Agent Space setup for AutoOps monitoring',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/setup_devops_agent.py --region us-east-1 --environment dev
  python scripts/setup_devops_agent.py --region ap-south-1 --environment prod --project myapp
        """
    )
    
    parser.add_argument(
        '--region',
        required=True,
        help='AWS region (e.g., us-east-1, ap-south-1)'
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
    
    # Run the setup
    setup = DevOpsAgentSetup(
        region=args.region,
        environment=args.environment,
        project_name=args.project
    )
    setup.run()


if __name__ == '__main__':
    main()
