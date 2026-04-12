# 🚨 AutoOps-Incident Intelligence with AWS DevOps Agent

<div align="center">

![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazonaws&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Slack](https://img.shields.io/badge/Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white)
![Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?style=for-the-badge&logo=awslambda&logoColor=white)

**An end-to-end AI-powered incident intelligence platform that automatically detects, investigates, and recommends remediation for AWS infrastructure issues.**

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Infrastructure Stack](#-infrastructure-stack)
- [Notification Flow](#-notification-flow)
- [DevOps Agent Investigation Phases](#-devops-agent-investigation-phases)
- [Project Structure](#-project-structure)
- [Setup & Deployment](#-setup--deployment)
- [Testing & Triggering Incidents](#-testing--triggering-incidents)
- [Screenshots](#-screenshots)
- [Key Design Decisions](#-key-design-decisions)

---

## 🔍 Overview

AutoOps is a fully automated incident intelligence system I built on AWS that eliminates the manual toil of on-call incident response. When a CloudWatch alarm fires, the system:

1. **Notifies** engineers via email and Slack immediately
2. **Triggers** an AI-powered investigation through the AWS DevOps Agent
3. **Analyzes** logs, traces, and metrics across the entire service topology
4. **Generates** a root cause analysis with supporting evidence
5. **Posts** findings to Slack with remediation recommendations
6. **Waits** for human approval before executing any fixes (HITL)

The system is intentionally designed with a **1 WCU DynamoDB table** to demonstrate real throttling, which triggers the full investigation pipeline end-to-end.

**API Endpoint:** `https://fpln1j5ayd.execute-api.us-east-1.amazonaws.com/dev`  
**AWS Account:** `478468758108` | **Region:** `us-east-1` | **Environment:** `dev`

---

## 🏗 Architecture

![Architecture Diagram](https://github.com/Naveen15github/AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent/blob/a071db53da7322afcf5c18168cb3a009454977f8/screenshots/Gemini_Generated_Image_ib14ytib14ytib14.png)


---

## ⚙️ Infrastructure Stack

### API Layer
- **API Gateway:** `autoops-api-dev` with CloudWatch access logging (structured JSON)
- **Routes:** `GET /health`, `GET /items`, `POST /items`, `GET /items/{id}`, `DELETE /items/{id}`, `POST /simulate-error`

### Compute Layer
- **Lambda:** `autoops-api-dev` — Python 3.12, 256 MB memory, 30s timeout
- **X-Ray:** Active tracing enabled on all invocations
- **Env vars:** `DYNAMODB_TABLE`, `ENVIRONMENT`

### Data Layer
- **DynamoDB:** `autoops-items-dev` — Provisioned billing, **intentionally 1 WCU** to demonstrate throttling
- **Schema:** `id` (PK, String), `name`, `description`, `createdAt`

### Storage Layer
- **S3:** `autoops-lambda-artifacts-dev-478468758108` — Lambda deployment packages, versioning enabled

### Monitoring & Alerting (6 CloudWatch Alarms)

| Alarm | Condition |
|---|---|
| `autoops-lambda-errors-dev` | Lambda errors ≥ 1 |
| `autoops-lambda-high-duration-dev` | Lambda duration > 3000ms |
| `autoops-lambda-throttles-dev` | Lambda throttles ≥ 1 |
| `autoops-dynamodb-write-throttles-dev` | DynamoDB write throttles ≥ 1 |
| `autoops-dynamodb-read-throttles-dev` | DynamoDB read throttles ≥ 1 |
| `autoops-api-5xx-errors-dev` | API Gateway 5XX errors ≥ 5 |

**CloudWatch Dashboard:** `autoops-dashboard-dev`  
Panels: Lambda errors/throttles, DynamoDB throttle events, Lambda P99 duration with anomaly detection, API Gateway request count and 5XX errors.

---

## 📡 Notification Flow

```
CloudWatch Alarm → ALARM State
        │
        ├──────────────────────────────────────────────────┐
        ▼                                                  ▼
SNS Topic: autoops-alarms-dev              EventBridge Rule (ALARM only)
        │                                                  │
        ├──► Email (naveen6662005@gmail.com)               │
        └──► AWS Chatbot → Slack #aws-incidents            ▼
                                          Lambda: autoops-devops-agent-webhook-dev
                                                           │
                                          ┌────────────────┤
                                          │ Secrets Manager│ (HMAC creds)
                                          └────────────────┤
                                                           │
                                          HMAC SHA-256 sign + POST
                                                           │
                                                           ▼
                                          DevOps Agent Space
                                          autoops-incident-intelligence
                                          ID: 238ad9b9-0c96-42e3-8290-deb05bd94b4e
```

### Webhook Payload Format

```json
{
  "eventType": "incident",
  "incidentId": "{alarmName}-{timestamp}",
  "action": "created",
  "priority": "HIGH",
  "title": "CloudWatch Alarm: {alarmName}",
  "description": "{reason}\n\nAlarm: {alarmName}\nState: {previousState} → {state}\nRegion: us-east-1\nAccount: 478468758108",
  "service": "autoops",
  "timestamp": "2026-04-13T01:04:00.000Z",
  "data": {
    "metadata": {
      "environment": "dev",
      "region": "us-east-1",
      "alarmArn": "arn:aws:cloudwatch:...",
      "configuration": {}
    }
  }
}
```

### Webhook Authentication
- **Method:** HMAC SHA-256
- **Message:** `{timestamp}:{payload}`
- **Headers:** `x-amzn-event-timestamp`, `x-amzn-event-signature`, `User-Agent: AWS-Lambda-DevOps-Agent-Integration/1.0`
- **Retry logic:** Exponential backoff, max 3 attempts, no retry on 4xx

---

## 🤖 DevOps Agent Investigation Phases

| Phase | Timeframe | What Happens |
|---|---|---|
| **Triage** | 0–20s | Duplicate check (20-min window); links if duplicate, proceeds if unique |
| **Topology Discovery** | 10–30s | Maps Lambda → DynamoDB → API Gateway relationships |
| **Log Analysis** | 30–60s | Queries `/aws/lambda/autoops-api-dev` for error patterns like `ProvisionedThroughputExceededException` |
| **Trace Analysis** | 1–2 min | X-Ray trace query; identifies failed DynamoDB write ops and causal API route |
| **Metrics Analysis** | 2–3 min | Confirms 1 WCU provisioned vs. actual consumption |
| **Root Cause Report** | 3–4 min | Natural-language analysis posted to Slack #aws-incidents |
| **HITL Workflow** | Post-report | Action buttons for remediation approval (real incidents only) |

### Real Incidents vs. Test Alarms

| | Test Alarms (`trigger_alarm.py`) | Real Incidents (`trigger_throttle.py`) |
|---|---|---|
| Trigger | Manual `SetAlarmState` API | Actual DynamoDB throttling |
| Investigation | Detected as test | Full root cause analysis |
| HITL Buttons | ❌ Not shown | ✅ Shown for approval |
| Slack Output | Status messages only | Full analysis + action buttons |

---

## 📁 Project Structure

```
autoops-incident-intelligence/
├── terraform/
│   ├── apigateway.tf          # API Gateway REST API + CloudWatch logging
│   ├── cloudwatch.tf          # 6 alarms + dashboard
│   ├── devops_agent.tf        # SSM params, EventBridge rule, webhook Lambda
│   ├── dynamodb.tf            # DynamoDB table (1 WCU intentional)
│   ├── iam.tf                 # IAM roles & policies
│   ├── lambda.tf              # Lambda function + X-Ray
│   ├── outputs.tf             # Terraform outputs
│   ├── providers.tf           # AWS provider config
│   ├── s3.tf                  # Artifact bucket
│   ├── sns.tf                 # SNS topic + email + Chatbot
│   ├── variables.tf           # Input variable definitions
│   ├── terraform.tfvars       # Actual values (gitignored in prod)
│   └── terraform.tfvars.example
├── lambda/
│   ├── index.py               # Main Lambda handler (CRUD + simulate-error)
│   └── requirements.txt
├── lambda_build/
│   └── function.zip           # Packaged deployment artifact
├── lambda_devops_agent/
│   └── lambda_function.py     # Webhook Lambda (EventBridge → DevOps Agent)
├── tests/
│   ├── test_api.py            # Full API test suite (9 tests)
│   ├── trigger_throttle.py    # Triggers real DynamoDB throttling (50 burst writes)
│   ├── trigger_alarm.py       # Manually sets alarm state
│   ├── health_check.sh        # Quick health verification
│   └── README.md
├── website/
│   └── index.html             # Static project landing page
├── docs/                      # Setup guides
└── README.md
```

---

## 🚀 Setup & Deployment

### Prerequisites

- AWS CLI configured with account `478468758108`
- Terraform >= 1.0
- Python 3.12
- Slack workspace with `#aws-incidents` channel

### Step 1 — Clone & Configure

```bash
git clone https://github.com/Naveen15github/AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent.git
cd AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent

cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform.tfvars with your values
```

`terraform.tfvars` contents:

```hcl
aws_region                       = "us-east-1"
environment                      = "dev"
owner_email                      = "your-email@example.com"
project_name                     = "autoops"
slack_workspace_id               = "T0ASAKXTZ0E"
slack_channel_id                 = "C0AS9A03X3P"
enable_devops_agent_integration  = true
devops_agent_webhook_secret_arn  = "arn:aws:secretsmanager:us-east-1:478468758108:secret:/autoops/dev/devops-agent-webhook-CD6fLC"
```

### Step 2 — Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

> ✅ **Apply complete! Resources: 7 added, 0 changed, 1 destroyed.**

### Step 3 — Post-Deployment Setup

1. **Confirm SNS email subscription** in your inbox
2. **Set up Slack** → follow `docs/03-slack-setup.md`
3. **Create DevOps Agent Space** → follow `docs/04-devops-agent-setup.md`
   - IAM Role to attach: `DevOpsAgentRole-AgentSpace-9u6cs7x4`
   - Policy ARN: `arn:aws:iam::478468758108:policy/autoops-devops-agent-observe-policy-dev`

### Step 4 — Connect DevOps Agent Resources

In the Agent Space (`autoops-incident-intelligence`), connect:

- **Lambda:** `autoops-api-dev`
- **DynamoDB:** `autoops-items-dev`
- **API Gateway:** `autoops-api-dev`
- **CloudWatch Log Groups:** `/aws/lambda/autoops-api-dev`, `/aws/apigateway/autoops-dev`
- **CloudWatch Alarms:** All 6 alarms
- **X-Ray:** Default group
- **Slack:** Workspace `T0ASAKXTZ0E`, Channel `C0AS9A03X3P` (`#aws-incidents`)

---

## 🧪 Testing & Triggering Incidents

### Run API Tests

```bash
cd tests
python test_api.py
```

Runs 9 tests covering all API routes including CRUD operations and error simulation.

### Health Check

```bash
bash tests/health_check.sh
```

### Trigger Real Throttling (Full Investigation Pipeline)

```bash
python tests/trigger_throttle.py --url https://fpln1j5ayd.execute-api.us-east-1.amazonaws.com/dev
```

This fires 50 burst POST requests at the 1 WCU DynamoDB table, causing ~90% throttle rate (≈45 throttled, ≈5 succeed). The full pipeline then runs:

| Time | Event |
|---|---|
| 0s | 50 write requests sent |
| ~1 min | CloudWatch alarm fires |
| ~1 min | Email + Slack notification via SNS/Chatbot |
| ~1 min | EventBridge triggers webhook Lambda |
| ~2 min | DevOps Agent begins topology discovery + log analysis |
| ~3–4 min | Root cause analysis posted to Slack |
| ~4 min | HITL action buttons appear for remediation approval |

### Trigger Test Alarm (No Real Issue)

```bash
python tests/trigger_alarm.py
```

Manually sets alarm state to ALARM. DevOps Agent will detect it as a test (no real metrics breached) and post investigation status only — no HITL buttons.

---

## 📸 Screenshots

### 1 — Terraform Init & Provider Installation

![Terraform Init](https://raw.githubusercontent.com/Naveen15github/AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent/65dc740667167b578c45c70b974d741ddf748984/screenshots/Screenshot%20(557).png)

*Terraform initializing the project — installing `hashicorp/aws v5.100.0` and `hashicorp/archive v2.7.1` providers, with successful lock file creation.*

---

### 2 — Terraform Plan — Resource Creation Preview

![Terraform Plan](https://raw.githubusercontent.com/Naveen15github/AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent/65dc740667167b578c45c70b974d741ddf748984/screenshots/Screenshot%20(558).png)

*`terraform plan` output showing all resources to be created — including the DevOps Agent IAM role SSM parameter, API endpoint SSM parameter, and the null resource for DevOps Agent instructions. DynamoDB table, Lambda, and S3 artifact bucket are all previewed.*

---

### 3 — Terraform Apply — Successful Deployment

![Terraform Apply](https://raw.githubusercontent.com/Naveen15github/AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent/65dc740667167b578c45c70b974d741ddf748984/screenshots/Screenshot%20(559).png)

*`terraform apply` completing successfully — 7 resources added. Outputs show the API endpoint, CloudWatch dashboard URL, DynamoDB table name, Lambda function name, S3 artifact bucket, SNS topic ARN, and next-step instructions.*

---

### 4 — AWS Chatbot — Slack Workspace Configuration

![AWS Chatbot Config](https://raw.githubusercontent.com/Naveen15github/AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent/65dc740667167b578c45c70b974d741ddf748984/screenshots/Screenshot%20(560).png)

*Amazon Q Developer in Chat Applications console showing the `aws-incidents` Slack workspace (`T0ASAKXTZ0E`) enabled and the `autoops-slac...` channel configuration mapping to `#aws-incidents`. This is the Chatbot integration that routes SNS alarm notifications directly into Slack.*

---

### 5 — Email Alert — Alarm Triggered

![Email Alert](https://raw.githubusercontent.com/Naveen15github/AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent/65dc740667167b578c45c70b974d741ddf748984/screenshots/Screenshot%20(562).png)

*SNS email notification fired at 1:04 AM showing the `autoops-lambda-errors-dev` alarm entering ALARM state, with the description "Testing DevOps Agent Slack integration". State change: OK → ALARM at Sunday 12 April, 2026 19:40:59 UTC.*

---

### 6 — Email Alert — Full Alarm Details

![Email Alert Full Details](https://raw.githubusercontent.com/Naveen15github/AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent/65dc740667167b578c45c70b974d741ddf748984/screenshots/Screenshot%20(563).png)

*Detailed view of the SNS email showing monitored metric configuration — `AWS/Lambda Errors` metric with `Sum` statistic over 60-second period, threshold `GreaterThanOrEqualTo 5.0`, `TreatMissingData: notBreaching`. State change actions route to `autoops-alarms-dev` SNS topic for both OK and ALARM states.*

---

### 7 — Slack — Investigation Linked (Duplicate Detection)

![Slack Investigation Linked](https://raw.githubusercontent.com/Naveen15github/AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent/65dc740667167b578c45c70b974d741ddf748984/screenshots/Screenshot%20(564).png)

*AWS DevOps Agent posting to `#aws-incidents` showing the triage deduplication in action. A second investigation was fired 7.5 minutes after the primary for the same `autoops-lambda-errors-dev` alarm. The Agent correctly identifies it as a duplicate and links it to the primary investigation instead of running a redundant full investigation.*

---

### 8 — Slack — Investigation Thread with CloudWatch Graph

![Slack Investigation Thread](https://raw.githubusercontent.com/Naveen15github/AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent/65dc740667167b578c45c70b974d741ddf748984/screenshots/Screenshot%20(565).png)

*The Slack thread showing the investigation link message alongside the AWS Chatbot alarm notification. The Chatbot posts an inline `AWS/Lambda Errors` CloudWatch graph showing the threshold line at 5.0 — the Agent cross-references this data during its investigation. The alarm state is shown as `OK` confirming this was a manually-triggered test.*

---

### 9 — AWS DevOps Agent — Investigation Timeline

![DevOps Agent Investigation Timeline](https://raw.githubusercontent.com/Naveen15github/AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent/65dc740667167b578c45c70b974d741ddf748984/screenshots/Screenshot%20(566).png)

*The DevOps Agent console showing the investigation timeline for `CloudWatch Alarm: autoops-lambda-errors-dev`. Investigation created at 01:04:21 and completed at 01:12:31. The Agent starts by reading alarm configuration, then queries actual Lambda Errors metrics and CloudTrail for the `SetAlarmState` API call — building its evidence chain.*

---

### 10 — AWS DevOps Agent — Root Cause Analysis Output

![DevOps Agent Root Cause](https://raw.githubusercontent.com/Naveen15github/AutoOps-Incident-Intelligence-with-AWS-DevOps-Agent/65dc740667167b578c45c70b974d741ddf748984/screenshots/Screenshot%20(567).png)

*The Agent's completed investigation findings. Key Evidence documented:*
- *No actual Lambda errors — `Errors` metric returned zero datapoints over 30 minutes*
- *Manual alarm state change detected — `StateReason` contains custom string "Testing DevOps Agent Slack integration" instead of an auto-generated threshold message*
- *CloudTrail confirms `SetAlarmState` API was called manually*

*Summary: "This is not a real incident" — threshold was never breached. The Agent correctly determines no remediation is needed and confirms the Slack integration is working.*

---

## 🔐 IAM Roles & Permissions

### `autoops-lambda-role-dev` (API Lambda)
- DynamoDB: `GetItem`, `PutItem`, `DeleteItem`, `Query`, `Scan` on `autoops-items-dev`
- CloudWatch Logs: `CreateLogGroup`, `CreateLogStream`, `PutLogEvents`
- X-Ray: `PutTraceSegments`, `PutTelemetryRecords`

### `autoops-devops-agent-lambda-role-dev` (Webhook Lambda)
- Lambda basic execution (CloudWatch Logs)
- Secrets Manager: `GetSecretValue` on webhook secret ARN

### `DevOpsAgentRole-AgentSpace-9u6cs7x4` (DevOps Agent)
- CloudWatch: Read metrics, logs, alarms
- Lambda: Read function configuration and logs
- DynamoDB: Read table metrics
- X-Ray: Read traces
- AWS Support: Create/update support cases

### `autoops-apigateway-cloudwatch-role`
- CloudWatch Logs: Full logging permissions for API Gateway access logs

---

## 🔑 Key Design Decisions

**1. Intentional 1 WCU DynamoDB** — The table is provisioned with 1 write capacity unit to make throttling easy to trigger with a burst of concurrent writes. This creates a real, observable incident rather than a synthetic one.

**2. EventBridge is Additive** — The EventBridge rule and webhook Lambda add the DevOps Agent notification channel without modifying existing SNS subscriptions, Chatbot configuration, or alarm thresholds. Email and Slack via Chatbot continue working unchanged.

**3. HMAC Authentication** — The webhook uses HMAC SHA-256 signing with a timestamp-prefixed message format. Credentials are stored in Secrets Manager and retrieved at runtime — never hardcoded.

**4. Triage Deduplication** — The Agent checks for duplicate investigations within a 20-minute window before starting a new one. If a duplicate is found, it links the new incident to the primary investigation rather than running redundant analysis.

**5. HITL for Real Incidents Only** — Remediation action buttons only appear when the Agent identifies a genuine resource issue with actual capacity mismatch. Test alarms (manually triggered via `SetAlarmState`) are correctly identified and produce investigation status only — no automated action is possible without a real problem to fix.

---

## 📊 Current System Status

| Component | Status |
|---|---|
| API Gateway + Lambda + DynamoDB | ✅ Working |
| CloudWatch Alarms (6) | ✅ Configured & firing correctly |
| Email notifications (SNS) | ✅ Working |
| Slack notifications (AWS Chatbot) | ✅ Working |
| EventBridge rule | ✅ Capturing alarm state changes |
| Webhook Lambda | ✅ Deployed & sending (200 OK) |
| DevOps Agent investigations | ✅ Completing with root cause analysis |
| Investigation results in Slack | ✅ Posting correctly |
| HITL action buttons | ⚠️ Appear only for real incidents (not test alarms — by design) |

---

## 📚 References

- [AWS DevOps Agent Documentation](https://docs.aws.amazon.com/devops-guru/latest/userguide/devops-guru-agent.html)
- [Amazon EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html)
- [AWS Chatbot](https://docs.aws.amazon.com/chatbot/latest/adminguide/what-is.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

---

<div align="center">

Built by **Naveen G** · [GitHub](https://github.com/Naveen15github)

</div>
