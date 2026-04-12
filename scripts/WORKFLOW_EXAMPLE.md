# Complete Setup Workflow Example

This guide shows the complete workflow from Terraform deployment to DevOps Agent monitoring.

## Step-by-Step Workflow

### 1. Deploy Infrastructure with Terraform

```bash
# Navigate to Terraform directory
cd terraform

# Initialize Terraform (first time only)
terraform init

# Review what will be created
terraform plan

# Deploy the infrastructure
terraform apply

# Verify outputs
terraform output
```

**Expected output:**
- API endpoint URL
- Lambda function name
- DynamoDB table name
- CloudWatch dashboard URL
- SNS topic ARN

### 2. Set Up DevOps Agent

```bash
# Return to project root
cd ..

# Run the automation script
python scripts/setup_devops_agent.py --region us-east-1 --environment dev
```

**What happens:**
- ✅ Creates IAM role for DevOps Agent
- ✅ Attaches observability policy
- ✅ Creates Agent Space
- ✅ Connects all resources
- ✅ Enables monitoring

**Time:** ~2-3 minutes

### 3. Verify Setup

```bash
# Run verification script
python scripts/verify_setup.py --region us-east-1 --environment dev
```

**Expected result:**
```
✅ Passed: 8
❌ Failed: 0
🎉 All checks passed!
```

### 4. Configure Slack Integration

**Manual step** (AWS Console):

1. Go to: https://console.aws.amazon.com/devops-agent
2. Select space: `autoops-incident-intelligence`
3. Click "Notifications" → "Configure Slack"
4. Authorize AWS Chatbot
5. Select your Slack channel

**Time:** ~5 minutes

### 5. Test the Setup

```bash
# Test API functionality
cd tests
python test_api.py

# Trigger an incident (DevOps Agent will detect it!)
python trigger_throttle.py
```

**Expected result:**
- API tests pass
- Throttle script triggers DynamoDB throttling
- CloudWatch alarm fires
- DevOps Agent detects the incident
- Slack notification appears in your channel 🎉

---

## Complete Script Example

Here's a complete bash script that automates the entire workflow:

```bash
#!/bin/bash
# complete_setup.sh - Full AutoOps setup automation

set -e  # Exit on error

REGION="us-east-1"
ENVIRONMENT="dev"
PROJECT="autoops"

echo "=========================================="
echo "  AutoOps Complete Setup"
echo "=========================================="
echo ""
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# Step 1: Deploy Terraform
echo "📋 Step 1: Deploying Terraform infrastructure..."
cd terraform
terraform init -upgrade
terraform apply -auto-approve
cd ..
echo "✅ Terraform deployed"
echo ""

# Step 2: Set up DevOps Agent
echo "📋 Step 2: Setting up DevOps Agent..."
python scripts/setup_devops_agent.py \
    --region "$REGION" \
    --environment "$ENVIRONMENT" \
    --project "$PROJECT"
echo "✅ DevOps Agent configured"
echo ""

# Step 3: Verify setup
echo "📋 Step 3: Verifying setup..."
python scripts/verify_setup.py \
    --region "$REGION" \
    --environment "$ENVIRONMENT" \
    --project "$PROJECT"
echo ""

# Step 4: Print next steps
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Configure Slack integration (5 minutes)"
echo "   → https://console.aws.amazon.com/devops-agent"
echo ""
echo "2. Test your setup:"
echo "   cd tests"
echo "   python test_api.py"
echo "   python trigger_throttle.py"
echo ""
echo "3. Check Slack for incident notifications!"
echo ""
```

Save this as `complete_setup.sh` and run:

```bash
chmod +x complete_setup.sh
./complete_setup.sh
```

---

## CI/CD Integration Example

### GitHub Actions

```yaml
name: Deploy AutoOps Infrastructure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install boto3
          
      - name: Deploy Terraform
        working-directory: terraform
        run: |
          terraform init
          terraform apply -auto-approve
      
      - name: Setup DevOps Agent
        run: |
          python scripts/setup_devops_agent.py \
            --region us-east-1 \
            --environment dev
      
      - name: Verify Setup
        run: |
          python scripts/verify_setup.py \
            --region us-east-1 \
            --environment dev
      
      - name: Run Tests
        working-directory: tests
        run: |
          python test_api.py
```

### GitLab CI

```yaml
stages:
  - deploy
  - verify
  - test

deploy_infrastructure:
  stage: deploy
  image: hashicorp/terraform:latest
  script:
    - cd terraform
    - terraform init
    - terraform apply -auto-approve
  only:
    - main

setup_devops_agent:
  stage: deploy
  image: python:3.9
  script:
    - pip install boto3
    - python scripts/setup_devops_agent.py --region us-east-1 --environment dev
  needs:
    - deploy_infrastructure
  only:
    - main

verify_setup:
  stage: verify
  image: python:3.9
  script:
    - pip install boto3
    - python scripts/verify_setup.py --region us-east-1 --environment dev
  needs:
    - setup_devops_agent
  only:
    - main

run_tests:
  stage: test
  image: python:3.9
  script:
    - cd tests
    - python test_api.py
  needs:
    - verify_setup
  only:
    - main
```

---

## Multi-Environment Setup

Deploy to multiple environments (dev, staging, prod):

```bash
#!/bin/bash
# multi_env_setup.sh

ENVIRONMENTS=("dev" "staging" "prod")
REGION="us-east-1"

for ENV in "${ENVIRONMENTS[@]}"; do
    echo "=========================================="
    echo "  Deploying to: $ENV"
    echo "=========================================="
    
    # Deploy Terraform
    cd terraform
    terraform workspace select "$ENV" || terraform workspace new "$ENV"
    terraform apply -auto-approve -var="environment=$ENV"
    cd ..
    
    # Setup DevOps Agent
    python scripts/setup_devops_agent.py \
        --region "$REGION" \
        --environment "$ENV"
    
    # Verify
    python scripts/verify_setup.py \
        --region "$REGION" \
        --environment "$ENV"
    
    echo "✅ $ENV deployment complete"
    echo ""
done

echo "🎉 All environments deployed!"
```

---

## Troubleshooting Workflow

If something goes wrong, follow this debugging workflow:

### 1. Check Terraform State

```bash
cd terraform
terraform show
terraform output
```

### 2. Verify AWS Resources

```bash
# Check if Lambda exists
aws lambda get-function --function-name autoops-api-dev --region us-east-1

# Check if DynamoDB table exists
aws dynamodb describe-table --table-name autoops-items-dev --region us-east-1

# Check if alarms exist
aws cloudwatch describe-alarms --alarm-name-prefix autoops --region us-east-1
```

### 3. Run Verification Script

```bash
python scripts/verify_setup.py --region us-east-1 --environment dev
```

### 4. Check IAM Role

```bash
# Check if role exists
aws iam get-role --role-name autoops-devops-agent-role-dev

# Check attached policies
aws iam list-attached-role-policies --role-name autoops-devops-agent-role-dev
```

### 5. Manual Cleanup (if needed)

```bash
# Delete DevOps Agent Space (if exists)
aws devops-agent delete-space --space-id <space-id> --region us-east-1

# Delete IAM role
aws iam detach-role-policy \
    --role-name autoops-devops-agent-role-dev \
    --policy-arn arn:aws:iam::ACCOUNT_ID:policy/autoops-devops-agent-observe-policy-dev

aws iam delete-role --role-name autoops-devops-agent-role-dev

# Destroy Terraform
cd terraform
terraform destroy -auto-approve
```

---

## Best Practices

### 1. Use Version Control

```bash
# .gitignore
terraform/.terraform/
terraform/*.tfstate
terraform/*.tfstate.backup
terraform/.terraform.lock.hcl
*.pyc
__pycache__/
.env
```

### 2. Secure Credentials

Never commit AWS credentials. Use:
- AWS CLI profiles
- Environment variables
- IAM roles (for EC2/ECS)
- GitHub Secrets (for CI/CD)

### 3. Test Before Production

```bash
# Always test in dev first
python scripts/setup_devops_agent.py --region us-east-1 --environment dev
python scripts/verify_setup.py --region us-east-1 --environment dev

# Then deploy to prod
python scripts/setup_devops_agent.py --region us-east-1 --environment prod
```

### 4. Monitor Costs

```bash
# Check AWS Cost Explorer
aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --filter file://cost-filter.json
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `terraform apply` | Deploy infrastructure |
| `python scripts/setup_devops_agent.py` | Setup monitoring |
| `python scripts/verify_setup.py` | Verify setup |
| `python tests/test_api.py` | Test API |
| `python tests/trigger_throttle.py` | Trigger incident |
| `terraform destroy` | Clean up everything |

---

## Need Help?

1. **Check documentation**: `scripts/README.md`, `scripts/QUICKSTART.md`
2. **Run verification**: `python scripts/verify_setup.py`
3. **Check AWS Console**: CloudWatch, DevOps Agent, IAM
4. **Review logs**: CloudWatch Logs for Lambda and API Gateway

Happy monitoring! 🚀
