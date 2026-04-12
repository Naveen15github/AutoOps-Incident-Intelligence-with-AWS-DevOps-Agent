# Step 3 — Slack Setup (Complete Guide)

This guide assumes you have NEVER used Slack before.
Every single step is explained with screenshots described in plain words.

Estimated time: 20 minutes

---

## What We Are Setting Up

We are connecting your AWS account to a Slack channel.
When your API has a problem, AWS will automatically send a message
to that Slack channel explaining what went wrong.

This involves two things:
1. Creating a Slack workspace and channel (if you don't have one)
2. Connecting AWS Chatbot to that channel

---

## PART 1 — Create a Slack Workspace

Skip this part if you already have a Slack workspace you can use.

### Step 1.1 — Sign Up for Slack

1. Open your web browser (Chrome, Firefox, Safari, Edge)
2. Go to: https://slack.com/get-started
3. Click the big green button "Create a new workspace"
4. Enter your email address and click "Continue"
5. Check your email for a 6-digit code from Slack
6. Enter that code on the Slack website
7. When asked "What's the name of your company or team?",
   type: `AutoOps Monitoring` (or any name you like)
8. When asked "What's your team working on?",
   type: `AWS DevOps Monitoring`
9. When asked to invite teammates, click "Skip this step"
10. Your workspace is created!

You are now inside your Slack workspace.
It looks like a chat application with a left sidebar.

---

### Step 1.2 — Create a Dedicated Channel

We need a channel specifically for AWS incident alerts.

1. Look at the left sidebar in Slack
2. You'll see "Channels" with a + sign next to it
3. Click the + sign next to "Channels"
4. Select "Create a channel"
5. In the "Name" field, type: `aws-incidents`
   (use lowercase, no spaces — Slack requires this)
6. In the "Description" field, type: `AWS DevOps Agent incident alerts`
7. Make sure "Private" is NOT selected (leave it as Public)
8. Click "Create"
9. When asked to add people, click "Skip for now"

You now have a channel called #aws-incidents in your workspace.

---

## PART 2 — Get Your Slack IDs

We need two ID numbers from Slack:
- Your **Workspace ID** (identifies your whole Slack workspace)
- Your **Channel ID** (identifies the #aws-incidents channel)

### Step 2.1 — Get Your Workspace ID

**Method A (Easiest — works in browser):**
1. Make sure you're using Slack in a web browser (not the app)
   - If using the app, click the three dots (···) at top
   - Select "Open in browser"
2. Look at the URL in your browser's address bar
3. It looks like: `https://app.slack.com/client/T0123ABCD/C0123ABCD`
4. The workspace ID is the part starting with **T** — it's `T0123ABCD` in this example
5. Copy just the T... part — that's your Workspace ID

**Method B (From workspace settings):**
1. Click your workspace name at the top left
2. Select "Settings & administration"
3. Select "Workspace settings"
4. The URL in your browser will contain your workspace ID starting with T

Write down your Workspace ID — it starts with T and is about 9-11 characters long.

---

### Step 2.2 — Get Your Channel ID

1. In Slack, right-click on the `#aws-incidents` channel in the left sidebar
2. Select "View channel details" (or "Copy link")
3. If you selected "View channel details":
   - A panel opens on the right
   - Scroll down to the very bottom
   - You'll see "Channel ID: C0123ABCD" — copy that value
4. If you selected "Copy link":
   - Paste it in a text file
   - The URL looks like: `https://app.slack.com/client/T0123ABCD/C0123ABCD`
   - The Channel ID is the SECOND code — starts with **C**

Write down your Channel ID — it starts with C and is about 9-11 characters long.

---

### Step 2.3 — Save These IDs in Terraform

Now open your `terraform/terraform.tfvars` file and fill in:

```hcl
slack_workspace_id = "T0123ABCD"   ← Your actual Workspace ID
slack_channel_id   = "C0123ABCD"   ← Your actual Channel ID
```

Save the file. These are needed for AWS Chatbot setup.

---

## PART 3 — Connect AWS Chatbot to Slack

AWS Chatbot is the service that sends AWS alarm messages into Slack.

### Step 3.1 — Open AWS Chatbot

1. Log into your AWS Console at https://console.aws.amazon.com
2. In the search bar at the top, type "Chatbot"
3. Click "AWS Chatbot" from the results
4. You're now on the AWS Chatbot page

---

### Step 3.2 — Configure a Slack Client

1. Under "Configure a chat client", you'll see a dropdown
2. Make sure "Slack" is selected in the dropdown
3. Click the orange "Configure client" button
4. A new tab opens asking you to sign in to Slack

---

### Step 3.3 — Authorize AWS in Slack

1. In the new tab, you'll see an "Allow" page from Slack
2. It says "AWS Chatbot is requesting permission to access your workspace"
3. Make sure the correct workspace is shown at the top right
   (it should show "AutoOps Monitoring" or whatever you named it)
4. If the wrong workspace is shown, click the workspace name
   and switch to the correct one
5. Click the green "Allow" button
6. The tab closes and you're back in AWS Console
7. You'll see "Slack" with a green connected indicator

---

### Step 3.4 — Create a Chatbot Channel Configuration

Now we connect the specific #aws-incidents channel:

1. Click "Create channel configuration" (or "Configure new channel")
2. Fill in the form:

   **Configuration name:**
   Type: `autoops-slack-alerts`

   **Logging:**
   Leave "Enabled" checked (or leave default)

   **Slack channel:**
   - Select "Private" or "Public"
   - Since we made it Public, select "Public channel"
   - Start typing `aws-incidents` in the channel search box
   - Select `#aws-incidents` from the dropdown

   **IAM permissions:**
   - Under "Role", select "Create an IAM role using a template"
   - Role name: type `autoops-chatbot-role`
   - Policy templates: select "Notification permissions"

   **Notifications — SNS topics:**
   - Click "Add SNS topic"
   - Region: select your region (e.g., US East (N. Virginia))
   - Topic: select `autoops-alarms-dev`
     (this is the SNS topic Terraform created)

3. Click "Configure" at the bottom

---

### Step 3.5 — Verify the Connection

1. After saving, you'll see your channel configuration listed
2. Click on it to open the details
3. Click the "Send test message" button
4. Go to Slack and check the `#aws-incidents` channel
5. You should see a test message from AWS appear in the channel

If you see the message: **Slack is connected successfully!**

If you don't see the message:
- Wait 1 minute and check again
- Make sure you confirmed your SNS email subscription (Step 2F of terraform guide)
- Check that you selected the right Slack channel

---

## PART 4 — Update Terraform with Slack IDs (Optional)

If you haven't done this yet, update your terraform.tfvars:

```hcl
slack_workspace_id = "T0123ABCD"
slack_channel_id   = "C0123ABCD"
```

Then run terraform apply again to save these values:
```
cd terraform
terraform apply -var-file="terraform.tfvars"
```

---

## Summary — What You Just Did

- ✅ Created a Slack workspace (or used existing)
- ✅ Created #aws-incidents channel
- ✅ Got your Workspace ID and Channel ID
- ✅ Connected AWS Chatbot to your Slack channel
- ✅ Linked the SNS alarm topic to Slack

Now when a CloudWatch alarm fires, the message goes:
```
CloudWatch Alarm → SNS Topic → AWS Chatbot → Slack #aws-incidents
```

AND when DevOps Agent investigates, the analysis goes:
```
DevOps Agent investigation → Slack #aws-incidents
```

---

## What Messages Look Like in Slack

When an alarm fires, you'll see a message like:

```
🚨 ALARM: autoops-dynamodb-write-throttles-dev
State: ALARM
Reason: Threshold Crossed: 15 out of the last 15 datapoints 
        [12.0 (26/04/26 03:15:00)] was greater than or equal 
        to the threshold (1.0).
```

When DevOps Agent finishes investigating, you'll see a more detailed message:

```
🔍 AWS DevOps Agent — Incident Analysis
Resource: autoops-api-dev (Lambda)
Root Cause: DynamoDB table autoops-items-dev is experiencing 
            write throttling. Provisioned WCU (1) is insufficient 
            for current write rate (47 WCU peak).
Recommendation: Increase write capacity to 10 WCU or switch to 
                On-Demand billing mode.
Confidence: HIGH
```

---

→ Next: `docs/04-devops-agent-setup.md`
