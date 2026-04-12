# Step 6 — Troubleshooting

Solutions for every common problem.

---

## Terraform Issues

### "Error: No valid credential sources found"
**Cause:** AWS CLI is not configured with your credentials.
**Fix:**
```
aws configure
```
Enter your Access Key ID and Secret Access Key when prompted.
Then run `terraform apply` again.

---

### "Error: S3 bucket already exists"
**Cause:** Another AWS account already has a bucket with the same name (bucket names are globally unique).
**Fix:** In `terraform.tfvars`, change `project_name` to something unique:
```hcl
project_name = "autoops-yourfirstname"
```
Then run `terraform apply` again.

---

### "Error: creating Lambda Function: InvalidParameterValueException"
**Cause:** Lambda zip file wasn't created properly.
**Fix:**
1. Make sure you're running terraform from inside the `terraform/` folder
2. Check the `lambda/` folder exists at the same level as `terraform/`
3. Run: `ls ../lambda/` — you should see `index.py`
4. Delete the `lambda_build/` folder if it exists and run terraform again

---

### "Error: creating CloudWatch Metric Alarm: ValidationError"
**Cause:** Usually a typo in dimension names.
**Fix:** Run `terraform plan` to identify the specific resource, then check `cloudwatch.tf` for the affected alarm. Make sure `FunctionName` and `TableName` dimensions match exactly.

---

### Terraform apply succeeds but no output values shown
**Fix:** Run `terraform output` to print them manually.

---

## API Issues

### Health check returns "Connection refused" or timeout
**Cause:** API Gateway is still propagating (takes 1-2 minutes after deploy).
**Fix:** Wait 2 minutes and try again.

---

### API returns 403 Forbidden
**Cause:** API Gateway deployment didn't complete properly.
**Fix:**
```
cd terraform
terraform apply -var-file="terraform.tfvars" -replace="aws_api_gateway_deployment.main"
```

---

### API returns 502 Bad Gateway
**Cause:** Lambda function is crashing on startup.
**Fix:** Check Lambda logs:
```
aws logs tail /aws/lambda/autoops-api-dev --follow
```
Look for Python errors in the output.

---

### POST /items returns 503 immediately (before throttle test)
**Cause:** DynamoDB table might be in a throttled state from a previous test.
**Fix:** Wait 5 minutes for DynamoDB to reset, then try again. This is actually normal behavior — it means the throttle test worked too well!

---

## Lambda Issues

### Lambda logs show "Unable to import module 'index'"
**Cause:** The Lambda package wasn't built correctly.
**Fix:**
1. Check the `lambda/index.py` file exists
2. Run: `terraform apply -var-file="terraform.tfvars" -replace="aws_s3_object.lambda_zip"`

---

### Lambda logs show "AccessDeniedException" for DynamoDB
**Cause:** IAM role policy wasn't attached correctly.
**Fix:**
```
terraform apply -var-file="terraform.tfvars" -replace="aws_iam_role_policy_attachment.lambda_dynamodb"
```

---

## Slack Issues

### No messages appear in #aws-incidents after test
**Cause:** SNS subscription email wasn't confirmed, OR Chatbot configuration isn't saving.
**Fix:**
1. Check your email for "AWS Notification - Subscription Confirmation"
2. Click the confirm link if you haven't
3. In AWS Chatbot, delete and recreate the channel configuration
4. Make sure you added the `autoops-alarms-dev` SNS topic to Chatbot

---

### AWS Chatbot shows "Workspace not found"
**Cause:** You need to complete the Slack authorization first.
**Fix:**
1. Go to AWS Chatbot console
2. Under "Configured clients", click "Configure new client"
3. Select "Slack" and click "Configure client"
4. Complete the Slack OAuth flow
5. Then create the channel configuration

---

### Slack shows "This app is not authorized to post"
**Cause:** AWS Chatbot app was removed from your Slack workspace.
**Fix:**
1. In Slack, go to workspace Settings → Manage Apps
2. Find "AWS Chatbot" and re-authorize it
3. Or redo the Chatbot setup from Step 3.2

---

## DevOps Agent Issues

### "DevOps Agent not found" or console page doesn't load
**Cause:** Your AWS Support plan is not Business or higher.
**Fix:**
1. Go to AWS Console → Support Center
2. Check your current support plan
3. Upgrade to Business Support if needed
4. Wait up to 1 hour for the DevOPS Agent console to appear

---

### DevOps Agent shows "Role verification failed"
**Cause:** The IAM Role ARN was entered incorrectly, or the role doesn't have the right permissions.
**Fix:**
1. Get the correct ARN: `terraform output devops_agent_role_arn`
2. In DevOps Agent console, edit your Agent Space
3. Re-enter the IAM role ARN exactly as shown (copy-paste, don't type manually)
4. Click "Verify role" — should show green checkmark

---

### DevOps Agent detects alarm but no analysis in Slack
**Cause:** Slack notification channel isn't configured in the Agent Space.
**Fix:**
1. In DevOps Agent console, open your Agent Space
2. Go to "Notifications" settings
3. Add your Slack workspace and #aws-incidents channel
4. Save and run the throttle test again

---

### Agent investigation shows "Insufficient data" or incomplete analysis
**Cause:** X-Ray tracing might not be fully enabled.
**Fix:**
1. Check that API Gateway stage has X-Ray enabled:
   ```
   terraform apply -var-file="terraform.tfvars" -replace="aws_api_gateway_stage.main"
   ```
2. Check Lambda has X-Ray active tracing:
   - Go to Lambda console → your function → Configuration → Monitoring
   - Under "Active tracing" it should show "Enabled"

---

## Throttle Test Issues

### Throttle test shows "0 throttled" (all requests succeed)
**Cause:** The 1 WCU limit allows occasional bursts, or your internet is too slow.
**Fix:**
```
python trigger_throttle.py --url https://YOUR_API_URL --count 200 --wave-delay 0
```
Increasing to 200 requests with no delay makes throttling certain.

---

### CloudWatch alarm doesn't fire after throttle test
**Cause:** CloudWatch alarms evaluate on 60-second periods — it takes up to 2 minutes.
**Fix:** Wait 2-3 minutes after the test completes. The alarm period is set to 60 seconds minimum.

---

## Check Logs Quickly

If something's not working, check these in order:

```bash
# 1. Check Lambda is running
aws logs tail /aws/lambda/autoops-api-dev --follow --since 10m

# 2. Check CloudWatch alarms state
aws cloudwatch describe-alarms --alarm-name-prefix autoops \
  --query 'MetricAlarms[*].[AlarmName,StateValue]' --output table

# 3. Check DynamoDB table exists
aws dynamodb describe-table --table-name autoops-items-dev \
  --query 'Table.[TableStatus,ProvisionedThroughput]'

# 4. Check SNS subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn $(terraform output -raw sns_topic_arn)
```

---

## Clean Up — Delete Everything

When you're done learning and want to avoid any accidental costs:

```bash
cd terraform
terraform destroy -var-file="terraform.tfvars"
```

Type `yes` when prompted. This deletes ALL resources Terraform created.

Note: DevOps Agent Space was created manually in the console.
Delete it manually: DevOps Agent Console → your Agent Space → Delete.

---

## Still Stuck?

1. Check the AWS documentation: https://docs.aws.amazon.com/devops-agent/
2. Check Terraform AWS provider docs: https://registry.terraform.io/providers/hashicorp/aws/
3. Check CloudWatch logs for your Lambda function — almost all problems show up there first
