# Step 1 — Prerequisites

Read this entire page before doing anything else.
It takes about 15 minutes to complete.

---

## What You Need

### 1. AWS Account

You need an AWS account. If you don't have one:

1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Fill in your email, password, and account name
4. Enter your credit card (required for verification, but free tier costs $0)
5. Choose "Basic Support" for now — you can upgrade later
6. Confirm your phone number
7. Select the "Free" support plan
8. Done — your account is ready in a few minutes

> NOTE: To use the real AWS DevOps Agent, you need at minimum
> "Business Support" (~$100/month). If you're learning on a
> personal account, you can still deploy all the infrastructure
> and trigger the alarms — you just won't see the Agent's
> automatic investigation. Everything else works the same.

---

### 2. AWS CLI (Command Line Tool)

The AWS CLI lets you talk to AWS from your computer's terminal.

**Windows:**
1. Go to https://aws.amazon.com/cli/
2. Click "Download for Windows"
3. Run the installer (.msi file)
4. Open Command Prompt and type: `aws --version`
5. You should see something like: `aws-cli/2.x.x`

**Mac:**
1. Open Terminal (press Cmd+Space, type "Terminal")
2. Type this command and press Enter:
   ```
   curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
   sudo installer -pkg AWSCLIV2.pkg -target /
   ```
3. Type: `aws --version` to confirm it worked

**Linux (Ubuntu/Debian):**
```
sudo apt-get update
sudo apt-get install -y unzip curl
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version
```

---

### 3. Configure AWS CLI with Your Credentials

You need to connect the AWS CLI to your AWS account.

**Step A — Create an IAM Access Key:**
1. Log into AWS Console at https://console.aws.amazon.com
2. Click your account name (top right corner)
3. Click "Security credentials"
4. Scroll down to "Access keys"
5. Click "Create access key"
6. Select "Command Line Interface (CLI)"
7. Check the confirmation box and click "Next"
8. Click "Create access key"
9. IMPORTANT: Copy both the "Access key ID" and "Secret access key"
   — you can only see the secret key once!

**Step B — Configure the CLI:**
1. Open your terminal
2. Type: `aws configure`
3. Enter your Access Key ID when prompted
4. Enter your Secret Access Key when prompted
5. Enter your region (type: `us-east-1` — easiest to start with)
6. Press Enter for output format (leave blank = json)

**Verify it works:**
```
aws sts get-caller-identity
```
You should see your account ID printed. If you do, AWS CLI is working.

---

### 4. Terraform

Terraform is the tool that creates all your AWS infrastructure automatically.

**Windows:**
1. Go to https://developer.hashicorp.com/terraform/downloads
2. Download the Windows AMD64 zip file
3. Extract the `terraform.exe` file
4. Move it to `C:\Windows\System32\` (so it works from any folder)
5. Open a NEW Command Prompt and type: `terraform -version`

**Mac:**
```
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
terraform -version
```
If you don't have Homebrew: go to https://brew.sh and follow install instructions first.

**Linux:**
```
sudo apt-get update && sudo apt-get install -y gnupg software-properties-common
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt-get install terraform
terraform -version
```

---

### 5. Python 3 (for running tests)

**Windows:**
1. Go to https://python.org/downloads
2. Download "Python 3.12" for Windows
3. Run installer — CHECK "Add Python to PATH" before clicking Install
4. Open a NEW Command Prompt: `python --version`

**Mac:**
```
brew install python3
python3 --version
```

**Linux:**
```
sudo apt-get install -y python3
python3 --version
```

---

### 6. A Text Editor

You need a text editor to fill in your configuration values.

Recommended: **Visual Studio Code** (free)
- Download from https://code.visualstudio.com
- Install the "HashiCorp Terraform" extension for syntax highlighting

Any text editor works: Notepad, TextEdit, Notepad++ etc.

---

## Checklist Before Moving On

Before going to Step 2, confirm all of these work:

```
aws --version           ← should print aws-cli/2.x.x
aws sts get-caller-identity  ← should print your account ID
terraform -version      ← should print Terraform v1.x.x
python3 --version       ← should print Python 3.x.x
```

If all four commands work, you're ready for Step 2.

→ Next: `docs/02-terraform-setup.md`
