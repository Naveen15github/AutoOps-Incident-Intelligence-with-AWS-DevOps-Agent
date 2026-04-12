# AutoOps Automation Scripts

This directory contains automation scripts for setting up and managing the AutoOps infrastructure.

## Scripts Overview

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `setup_devops_agent.py` | Automates DevOps Agent Space creation | After `terraform apply` |
| `verify_setup.py` | Verifies setup is complete | After running setup script |

---

## setup_devops_agent.py

Automates the creation and configuration of an AWS DevOps Agent Space for monitoring your serverless API.

### What It Does

1. **Creates IAM Role** - Sets up the `autoops-devops-agent-role-dev` with proper trust policy for `devops-agent.amazonaws.com`
2. **Attaches Policy** - Links the existing observability policy created by Terraform
3. **Retrieves Resources** - Pulls Lambda, DynamoDB, API Gateway, and CloudWatch alarm information from Terraform outputs (stored in SSM)
4. **Creates Agent Space** - Uses AWS CLI to create the DevOps Agent Space
5. **Connects Resources** - Automatically connects:
   - CloudWatch log groups (`/aws/lambda/*` and `/aws/apigateway/*`)
   - All 6 CloudWatch alarms
   - Lambda function
   - DynamoDB table
   - API Gateway
   - Enables X-Ray tracing

### Prerequisites

```bash
# Install required Python packages
pip install boto3

# Ensure AWS CLI is installed and configured
aws --version

# Verify Terraform has been applied
cd terraform && terraform output
```

### Usage

```bash
# Basic usage (defaults to 'dev' environment and 'autoops' project)
python scripts/setup_devops_agent.py --region us-east-1

# Specify environment
python scripts/setup_devops_agent.py --region us-east-1 --environment dev

# Custom project name
python scripts/setup_devops_agent.py --region ap-south-1 --environment prod --project myapp
```

### Command-Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--region` | Yes | - | AWS region (e.g., us-east-1, ap-south-1) |
| `--environment` | No | dev | Environment name (dev, staging, prod) |
| `--project` | No | autoops | Project name prefix |

### What Happens If...

**AWS CLI doesn't support `devops-agent` commands:**
- The script will detect this and print manual setup instructions
- You can complete the setup in the AWS Console
- The IAM role will still be created for you

**Resources already exist:**
- The script is idempotent - it checks before creating
- Existing resources are reused without errors
- Safe to run multiple times

**Terraform outputs are missing:**
- The script will attempt to use naming conventions as fallback
- If that fails, you'll get a clear error message
- Make sure `terraform apply` completed successfully

### Output Example

```
======================================================================
  AWS DevOps Agent Setup - DEV
======================================================================

Region: us-east-1
Environment: dev
Project: autoops
Account ID: 478468758108

📋 Step 1: Creating IAM Role for DevOps Agent
✅ Created IAM role: arn:aws:iam::478468758108:role/autoops-devops-agent-role-dev

📋 Step 2: Attaching observability policy to role
✅ Attached policy: arn:aws:iam::478468758108:policy/autoops-devops-agent-observe-policy-dev

📋 Step 3: Retrieving resource information from Terraform outputs
ℹ️  Lambda function: autoops-api-dev
ℹ️  DynamoDB table: autoops-items-dev
ℹ️  CloudWatch alarms: 6 alarms found
ℹ️  API Gateway ID: abc123xyz

📋 Step 4: Creating DevOps Agent Space
✅ Created Agent Space: autoops-incident-intelligence
✅ Space ID: space-abc123

📋 Step 5: Connecting resources to Agent Space
✅ Connected log group: /aws/lambda/autoops-api-dev
✅ Connected log group: /aws/apigateway/autoops-dev
✅ Connected alarm: lambda-errors
✅ Connected alarm: lambda-duration
✅ Connected alarm: lambda-throttles
✅ Connected alarm: dynamodb-write-throttles
✅ Connected alarm: dynamodb-read-throttles
✅ Connected alarm: api-5xx
✅ Connected Lambda: autoops-api-dev
✅ Connected DynamoDB: autoops-items-dev
✅ Connected API Gateway: abc123xyz
✅ Enabled X-Ray tracing

======================================================================
  NEXT STEP: SLACK INTEGRATION
======================================================================

AWS DevOps Agent Space is ready! Now set up Slack notifications:

1. Open the AWS Console:
   https://console.aws.amazon.com/devops-agent

2. Select your space: autoops-incident-intelligence

3. Go to 'Notifications' tab

4. Click 'Configure Slack'

5. Follow the guided setup to:
   - Authorize AWS Chatbot with your Slack workspace
   - Select the channel for notifications
   - Configure notification preferences

6. Test the integration:
   cd tests && python trigger_throttle.py

For detailed instructions, see: docs/03-slack-setup.md

======================================================================
  SETUP COMPLETE
======================================================================
✅ DevOps Agent IAM role is ready
✅ DevOps Agent Space is configured
```

### Troubleshooting

**Error: "boto3 is not installed"**
```bash
pip install boto3
```

**Error: "AWS CLI does not support 'devops-agent' commands"**
- Update AWS CLI: `pip install --upgrade awscli`
- Or use the manual instructions printed by the script
- DevOps Agent might not be available in your region yet

**Error: "Failed to retrieve Terraform outputs"**
- Ensure Terraform has been applied: `cd terraform && terraform apply`
- Check SSM parameters exist: `aws ssm get-parameters-by-path --path /autoops/dev`

**Error: "Access Denied" when creating IAM role**
- Ensure your AWS credentials have IAM permissions
- Required permissions: `iam:CreateRole`, `iam:AttachRolePolicy`, `iam:GetRole`

**Error: "DevOps Agent service not available"**
- Check if the service is available in your region
- Try a different region (us-east-1 typically has new services first)
- Fall back to manual setup in the Console

### Manual Setup Alternative

If the automated script doesn't work, you can set up manually:

1. **Create IAM Role** (the script will still do this for you):
   - Role name: `autoops-devops-agent-role-dev`
   - Trust policy: `devops-agent.amazonaws.com`
   - Attach policy: `arn:aws:iam::478468758108:policy/autoops-devops-agent-observe-policy-dev`

2. **Create Agent Space in Console**:
   - Go to: https://console.aws.amazon.com/devops-agent
   - Click "Create Agent Space"
   - Name: `autoops-incident-intelligence`
   - Description: "Monitors the AutoOps serverless API"
   - Select the IAM role created above

3. **Connect Resources**:
   - Add log groups: `/aws/lambda/autoops-api-dev`, `/aws/apigateway/autoops-dev`
   - Add all 6 CloudWatch alarms
   - Add Lambda function, DynamoDB table, API Gateway
   - Enable X-Ray tracing

### Next Steps After Running This Script

1. **Set up Slack integration** (manual step required):
   - See `docs/03-slack-setup.md` for detailed instructions
   - Configure AWS Chatbot in the Console
   - Connect your Slack workspace and channel

2. **Test the setup**:
   ```bash
   cd tests
   python test_api.py          # Test API functionality
   python trigger_throttle.py  # Trigger an incident
   ```

3. **Monitor in DevOps Agent**:
   - Open the AWS Console
   - Navigate to DevOps Agent
   - View your space dashboard
   - Check Slack for incident notifications

### Integration with Terraform

This script complements your Terraform infrastructure:

- **Terraform creates**: Lambda, DynamoDB, API Gateway, CloudWatch alarms, IAM policies
- **This script creates**: DevOps Agent IAM role and Agent Space
- **Manual step**: Slack integration (AWS Chatbot)

The script reads Terraform outputs from SSM Parameter Store, so it automatically stays in sync with your infrastructure.

### Security Notes

- The IAM role follows least-privilege principles
- Only read-only observability permissions are granted
- No write access to your infrastructure
- Trust policy restricts access to DevOps Agent service only

### Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the script output for specific error messages
3. Verify prerequisites are met
4. Try the manual setup alternative if automation fails

---

## verify_setup.py

Verification script to check if your DevOps Agent setup is complete and properly configured.

### What It Checks

1. ✅ IAM role exists with correct name
2. ✅ Trust policy allows `devops-agent.amazonaws.com`
3. ✅ Observability policy is attached to the role
4. ✅ Terraform outputs are accessible (DynamoDB, API Gateway, alarms)
5. ✅ DevOps Agent Space exists (optional check)

### Usage

```bash
# Basic verification
python scripts/verify_setup.py --region us-east-1

# Specify environment
python scripts/verify_setup.py --region us-east-1 --environment dev

# Custom project name
python scripts/verify_setup.py --region ap-south-1 --environment prod --project myapp
```

### Output Example

```
======================================================================
  DevOps Agent Setup Verification - DEV
======================================================================

Region: us-east-1
Environment: dev
Project: autoops
Account ID: 478468758108

🔍 Checking IAM role...
✅ IAM role exists: arn:aws:iam::478468758108:role/autoops-devops-agent-role-dev
✅ Trust policy is correct (devops-agent.amazonaws.com)

🔍 Checking policy attachment...
✅ Policy is attached: autoops-devops-agent-observe-policy-dev

🔍 Checking Terraform outputs...
✅ DynamoDB table: autoops-items-dev
✅ API endpoint: https://abc123xyz.execute-api.us-east-1.amazo...
✅ Alarm ARNs: 6 alarms found

🔍 Checking DevOps Agent Space...
✅ DevOps Agent Space exists: autoops-incident-intelligence
   Space ID: space-abc123

======================================================================
  VERIFICATION SUMMARY
======================================================================

Total checks: 8
✅ Passed: 8
❌ Failed: 0

🎉 All checks passed! Your setup is complete.

Next steps:
1. Set up Slack integration (see scripts/QUICKSTART.md)
2. Test your API: cd tests && python test_api.py
3. Trigger an incident: python tests/trigger_throttle.py
```

### When to Use

- **After running `setup_devops_agent.py`** - Verify everything was created correctly
- **Before testing** - Ensure infrastructure is ready
- **Troubleshooting** - Identify what's missing or misconfigured
- **CI/CD pipelines** - Automated verification in deployment workflows

### Exit Codes

- `0` - All checks passed
- `1` - One or more checks failed

This makes it perfect for CI/CD:
```bash
python scripts/verify_setup.py --region us-east-1 && echo "Ready to deploy!"
```
