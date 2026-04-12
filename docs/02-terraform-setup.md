# Step 2 — Deploy with Terraform

This step creates ALL your AWS infrastructure automatically.
Lambda, DynamoDB, API Gateway, CloudWatch alarms, IAM roles — everything.

Estimated time: 10 minutes

---

## Part A — Fill In Your Configuration

1. Open the `terraform/` folder in your text editor

2. Find the file called `terraform.tfvars.example`

3. Create a COPY of it named `terraform.tfvars`
   - On Mac/Linux terminal: `cp terraform/terraform.tfvars.example terraform/terraform.tfvars`
   - On Windows: right-click the file → Copy → Paste → rename to `terraform.tfvars`

4. Open `terraform.tfvars` and fill in YOUR values:

```hcl
# Change this to your preferred AWS region
aws_region = "us-east-1"

# Keep as "dev" for learning
environment = "dev"

# IMPORTANT: Put YOUR email here — you'll get alarm notifications
owner_email = "yourname@gmail.com"   ← CHANGE THIS

# Leave as-is
project_name = "autoops"

# Leave empty for now — you'll fill these after Slack setup (Step 3)
slack_workspace_id = ""
slack_channel_id   = ""
```

5. Save the file

> IMPORTANT: Never share your `terraform.tfvars` file publicly.
> It contains your email. The `.gitignore` is already set to exclude it.

---

## Part B — Initialize Terraform

This downloads the AWS provider plugins Terraform needs.
You only do this once.

1. Open your terminal
2. Navigate to the terraform folder:
   ```
   cd path/to/autoops-incident-intelligence/terraform
   ```
   Example paths:
   - Windows: `cd C:\Users\YourName\Downloads\autoops\terraform`
   - Mac: `cd ~/Downloads/autoops/terraform`

3. Run:
   ```
   terraform init
   ```

4. You should see:
   ```
   Terraform has been successfully initialized!
   ```

If you see any errors, check that:
- You're in the `terraform/` folder (not the root folder)
- Terraform is installed correctly (`terraform -version`)
- You have internet access

---

## Part C — Preview What Will Be Created

Before actually creating anything, preview the plan:

```
terraform plan -var-file="terraform.tfvars"
```

Terraform will print a long list of resources it will create.
Look for this at the bottom:

```
Plan: 28 to add, 0 to change, 0 to destroy.
```

The exact number may differ slightly. As long as it says "0 to destroy"
you're safe to proceed.

Read through the list — you'll see Lambda, DynamoDB, API Gateway,
CloudWatch alarms, IAM roles, S3 bucket etc. being created.

---

## Part D — Deploy Everything

When you're ready, run:

```
terraform apply -var-file="terraform.tfvars"
```

Terraform will show the plan again and ask:
```
Do you want to perform these actions? 
  Enter a value: 
```

Type `yes` and press Enter.

Watch the output as resources are created. It takes 3-5 minutes.

When complete you'll see something like:
```
Apply complete! Resources: 28 added, 0 changed, 0 destroyed.

Outputs:

api_endpoint = "https://abc123.execute-api.us-east-1.amazonaws.com/dev"
devops_agent_role_arn = "arn:aws:iam::123456789:role/autoops-devops-agent-role-dev"
lambda_function_name = "autoops-api-dev"
dynamodb_table_name = "autoops-items-dev"
...
```

---

## Part E — COPY THESE VALUES (Important!)

After `terraform apply` completes, it prints several output values.
**Copy all of them to a text file right now** — you'll need them in later steps.

The most important ones:

| Output | Where You'll Use It |
|---|---|
| `api_endpoint` | Website config, test scripts |
| `devops_agent_role_arn` | DevOps Agent setup (Step 4) |
| `lambda_function_name` | DevOps Agent setup (Step 4) |
| `dynamodb_table_name` | DevOps Agent setup (Step 4) |
| `cloudwatch_dashboard_url` | Monitoring |

If you lose these values, you can always get them back by running:
```
terraform output
```

---

## Part F — Confirm Your Email Subscription

After `terraform apply`, AWS sends you an email with the subject:
**"AWS Notification - Subscription Confirmation"**

1. Check your inbox (check spam folder if not there)
2. Open the email
3. Click the "Confirm subscription" link
4. You'll see "Subscription confirmed!"

This is required. Without confirming, you won't receive CloudWatch alarm emails.

---

## What Was Created

Here's a summary of everything Terraform just built for you:

```
Lambda Function:    autoops-api-dev
DynamoDB Table:     autoops-items-dev
API Gateway:        autoops-api-dev (REST API)
CloudWatch Alarms:  6 alarms (errors, throttles, latency, 5XX)
CloudWatch Dashboard: autoops-dashboard-dev
SNS Topic:          autoops-alarms-dev (with your email subscribed)
S3 Bucket:          autoops-lambda-artifacts-dev-{account_id}
IAM Roles:          Lambda exec, DevOps Agent, ChatBot
SSM Parameters:     3 params storing key values
```

---

## Verify the Deployment

Run a quick health check to confirm everything is working:

**Mac/Linux:**
```
cd ../tests
chmod +x health_check.sh
./health_check.sh https://YOUR_API_ENDPOINT_FROM_OUTPUT/dev
```

**Windows or all platforms (Python):**
```
cd tests
python test_api.py --url https://YOUR_API_ENDPOINT_FROM_OUTPUT/dev
```

Replace `YOUR_API_ENDPOINT_FROM_OUTPUT` with the actual URL from terraform output.

You should see all tests passing with green checkmarks.

---

## Troubleshooting

**"Error: No valid credential sources found"**
→ Run `aws configure` again. Make sure you entered the correct access key.

**"Error: S3 bucket already exists"**
→ The bucket name is already taken globally. Change `project_name` in tfvars to something unique like `"autoops-yourname"`.

**"Error creating Lambda Function: InvalidParameterValueException"**
→ The Lambda zip wasn't created properly. Make sure you're running terraform from the `terraform/` folder and the `lambda/` folder exists at the same level.

**Tests fail with "Connection refused" or timeout**
→ Wait 1-2 minutes after terraform apply — API Gateway can take a moment to become active.

---

→ Next: `docs/03-slack-setup.md`
