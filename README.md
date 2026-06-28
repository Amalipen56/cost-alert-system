# Automated Cloud Cost Alert System

An event-driven serverless system that monitors AWS spend and delivers automated cost reports to your inbox. Zero servers — entirely Lambda, SNS, EventBridge, and AWS Budgets.

## How it works

**Flow 1 — Budget breach alert:**
AWS Budgets detects spend > 80% of monthly limit → publishes to SNS → triggers Alert Lambda → Lambda calls Cost Explorer API → sends formatted email with service breakdown and right-sizing recommendations

**Flow 2 — Weekly scheduled report:**
EventBridge cron (every Sunday 8AM UTC) → triggers Weekly Lambda → Lambda queries Cost Explorer for last 7 days → sends daily breakdown + 30-day trend + anomaly detection email

## What the emails contain

**Alert email:**
- Total spend this month
- Projected end-of-month cost
- Top 5 cost-driving services with percentages
- Compute Optimizer right-sizing recommendations
- Full service breakdown

**Weekly report email:**
- 7-day total and daily average
- Visual daily bar chart (text-based)
- Peak spend day
- Cost by service with percentages
- Anomaly detection warnings

## Infrastructure (Terraform)

| Resource | Purpose |
|---|---|
| AWS Budgets | Monitors monthly spend, triggers SNS at threshold |
| SNS Topic | Message bus — receives from Budgets, fans out to Lambda and email |
| SNS Email subscription | Delivers formatted reports to inbox |
| Alert Lambda (Python 3.11) | Generates cost breakdown on budget breach |
| Weekly Lambda (Python 3.11) | Generates weekly summary every Sunday |
| EventBridge rule | cron(0 8 ? * SUN *) — triggers weekly Lambda |
| IAM Role | Least-privilege: Cost Explorer read, SNS publish, CloudWatch logs |

## Stack

AWS Lambda · SNS · EventBridge · AWS Budgets · Cost Explorer API · Compute Optimizer API · Terraform · Python 3.11

## Built by

Amali Emmanuel — amaliemmanuel40@gmail.com
