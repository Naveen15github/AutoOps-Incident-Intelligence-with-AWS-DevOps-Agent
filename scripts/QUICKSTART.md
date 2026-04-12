# Quick Start: DevOps Agent Setup

Get your AWS DevOps Agent Space up and running in 5 minutes.

## Prerequisites Check

```bash
# 1. Check AWS CLI
aws --version

# 2. Check Python and boto3
python3 --version
pip install boto3

# 3. Verify Terraform is deployed
cd terraform
terraform output
cd ..
```

## Run the Script

```bash
# One command to set everything up
python scripts/setup_devops_agent.py --region us-east-1 --environment dev
```

That's it! The script will:
- ✅ Create IAM role for DevOps Agent
- ✅ Attach observability policy
- ✅ Create Agent Space
- ✅ Connect all resources (Lambda, DynamoDB, API Gateway)
- ✅ Connect CloudWatch logs and alarms
- ✅ Enable X-Ray tracing

## What's Next?

### 1. Set Up Slack (5 minutes)

The script will print instructions, but here's the quick version:

1. Go to: https://console.aws.amazon.com/devops-agent
2. Select your space: `autoops-incident-intelligence`
3. Click "Notifications" → "Configure Slack"
4. Authorize AWS Chatbot with your Slack workspace
5. Select your channel

### 2. Test It (2 minutes)

```bash
cd tests

# Test normal API operations
python test_api.py

# Trigger an incident (DevOps Agent will detect it!)
python trigger_throttle.py
```

Check your Slack channel - you should see an incident notification! 🎉

## Troubleshooting

**Script fails with "devops-agent commands not supported"?**
- The script will print manual setup instructions
- Follow them in the AWS Console
- The IAM role is still created for you

**Can't find Terraform outputs?**
```bash
cd terraform
terraform output
```
If empty, run `terraform apply` first.

**Need help?**
- See full documentation: `scripts/README.md`
- Check Terraform config: `terraform/devops_agent.tf`

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS DevOps Agent Space                    │
│                 autoops-incident-intelligence                │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ monitors
                              ▼
        ┌─────────────────────────────────────────┐
        │         Your Infrastructure             │
        ├─────────────────────────────────────────┤
        │  • Lambda Function (autoops-api-dev)    │
        │  • DynamoDB Table (autoops-items-dev)   │
        │  • API Gateway (autoops-dev)            │
        │  • CloudWatch Logs & Alarms (6 alarms)  │
        │  • X-Ray Traces                         │
        └─────────────────────────────────────────┘
                              │
                              │ notifies
                              ▼
                    ┌──────────────────┐
                    │  Slack Channel   │
                    │  #autoops-alerts │
                    └──────────────────┘
```

## What the Script Creates

| Resource | Name | Purpose |
|----------|------|---------|
| IAM Role | `autoops-devops-agent-role-dev` | Allows DevOps Agent to read your resources |
| Agent Space | `autoops-incident-intelligence` | Monitors your infrastructure |
| Connections | 6 CloudWatch alarms | Detects errors, throttles, high latency |
| Connections | 2 log groups | Analyzes Lambda and API Gateway logs |
| Connections | 3 AWS resources | Monitors Lambda, DynamoDB, API Gateway |

## Cost Estimate

AWS DevOps Agent pricing (as of 2024):
- **Free tier**: First 1M events/month
- **After free tier**: ~$0.50 per 1M events

For this demo project: **Effectively free** (well within free tier)

## Security

The IAM role created has **read-only** permissions:
- ✅ Can read CloudWatch metrics and logs
- ✅ Can read X-Ray traces
- ✅ Can describe Lambda, DynamoDB, API Gateway
- ❌ Cannot modify any resources
- ❌ Cannot access data in DynamoDB
- ❌ Cannot execute Lambda functions

## Support

Need help? Check these resources:
1. **Full documentation**: `scripts/README.md`
2. **Terraform config**: `terraform/devops_agent.tf`
3. **Slack setup guide**: `docs/03-slack-setup.md`
4. **AWS DevOps Agent docs**: https://docs.aws.amazon.com/devops-agent/

---

**Ready to go?** Run the script and watch the magic happen! ✨

```bash
python scripts/setup_devops_agent.py --region us-east-1 --environment dev
```
