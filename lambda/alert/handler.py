import json
import boto3
import os
from datetime import datetime, timezone, timedelta

ce_client = boto3.client("ce")
sns_client = boto3.client("sns")

SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
BUDGET_NAME = os.environ.get("BUDGET_NAME", "monthly-budget")


def lambda_handler(event, context):
    print("Budget alert triggered:", json.dumps(event))

    try:
        # Get current month date range
        now = datetime.now(timezone.utc)
        start = now.replace(day=1).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")

        # If start equals end (first day of month) shift end forward
        if start == end:
            end = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        # Get spend breakdown by service for current month
        response = ce_client.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )

        results = response["ResultsByTime"][0]["Groups"]

        # Sort services by cost descending
        services = sorted(
            [
                {
                    "service": r["Keys"][0],
                    "cost": float(r["Metrics"]["UnblendedCost"]["Amount"]),
                    "unit": r["Metrics"]["UnblendedCost"]["Unit"],
                }
                for r in results
            ],
            key=lambda x: x["cost"],
            reverse=True,
        )

        # Total spend this month
        total = sum(s["cost"] for s in services)

        # Project end of month spend
        days_in_month = 31
        day_of_month = now.day
        projected = (total / day_of_month) * days_in_month if day_of_month > 0 else 0

        # Get top 5 cost drivers
        top_services = services[:5]

        # Build email
        subject = f"AWS Budget Alert — ${total:.2f} spent this month"

        lines = [
            "=" * 56,
            "  AWS CLOUD COST ALERT",
            "=" * 56,
            "",
            f"  Budget:       {BUDGET_NAME}",
            f"  Period:       {start} to {end}",
            f"  Total spent:  ${total:.2f}",
            f"  Projected:    ${projected:.2f} by end of month",
            "",
            "-" * 56,
            "  TOP COST DRIVERS",
            "-" * 56,
        ]

        for i, svc in enumerate(top_services, 1):
            pct = (svc["cost"] / total * 100) if total > 0 else 0
            lines.append(f"  {i}. {svc['service'][:38]}")
            lines.append(f"     ${svc['cost']:.4f}  ({pct:.1f}% of total)")

        lines += [
            "",
            "-" * 56,
            "  RIGHT-SIZING RECOMMENDATIONS",
            "-" * 56,
        ]

        # Get Compute Optimizer recommendations
        try:
            optimizer = boto3.client("compute-optimizer")
            ec2_recs = optimizer.get_ec2_instance_recommendations()
            recs = ec2_recs.get("instanceRecommendations", [])

            if recs:
                for rec in recs[:3]:
                    instance = rec.get("instanceArn", "").split("/")[-1]
                    current = rec.get("currentInstanceType", "unknown")
                    options = rec.get("recommendationOptions", [])
                    if options:
                        recommended = options[0].get("instanceType", "unknown")
                        saving = options[0].get("estimatedMonthlySavings", {})
                        saving_amt = saving.get("value", 0)
                        lines.append(f"  Instance: {instance}")
                        lines.append(f"  Current:  {current}  ->  Recommended: {recommended}")
                        lines.append(f"  Est. monthly saving: ${saving_amt:.2f}")
                        lines.append("")
            else:
                lines.append("  No right-sizing recommendations at this time.")
        except Exception as e:
            lines.append(f"  Could not fetch recommendations: {str(e)[:80]}")

        lines += [
            "",
            "-" * 56,
            "  ALL SERVICES THIS MONTH",
            "-" * 56,
        ]

        for svc in services:
            if svc["cost"] > 0.0001:
                lines.append(f"  {svc['service'][:38]:<38}  ${svc['cost']:.4f}")

        lines += [
            "",
            "=" * 56,
            "  View full breakdown: https://console.aws.amazon.com/cost-management/home",
            "=" * 56,
        ]

        message = "\n".join(lines)

        # Publish to SNS
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message,
        )

        print(f"Alert sent. Total: ${total:.2f}, Projected: ${projected:.2f}")
        return {"statusCode": 200, "body": f"Alert sent. Total spend: ${total:.2f}"}

    except Exception as e:
        print(f"Error: {str(e)}")
        raise