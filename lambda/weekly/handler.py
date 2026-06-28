import json
import boto3
import os
from datetime import datetime, timezone, timedelta
from collections import defaultdict

ce_client = boto3.client("ce")
sns_client = boto3.client("sns")

SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")


def lambda_handler(event, context):
    print("Weekly cost report triggered")

    try:
        now = datetime.now(timezone.utc)

        # Last 7 days
        end = now.strftime("%Y-%m-%d")
        start = (now - timedelta(days=7)).strftime("%Y-%m-%d")

        # Last 30 days for trend
        start_30 = (now - timedelta(days=30)).strftime("%Y-%m-%d")

        # Get daily spend for last 7 days
        daily_response = ce_client.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )

        daily_costs = []
        for result in daily_response["ResultsByTime"]:
            date = result["TimePeriod"]["Start"]
            cost = float(result["Total"]["UnblendedCost"]["Amount"])
            daily_costs.append({"date": date, "cost": cost})

        week_total = sum(d["cost"] for d in daily_costs)

        # Get spend by service for last 7 days
        service_response = ce_client.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )

        services = sorted(
            [
                {
                    "service": r["Keys"][0],
                    "cost": float(r["Metrics"]["UnblendedCost"]["Amount"]),
                }
                for r in service_response["ResultsByTime"][0]["Groups"]
            ],
            key=lambda x: x["cost"],
            reverse=True,
        )

        # Get last 30 days total for comparison
        month_response = ce_client.get_cost_and_usage(
            TimePeriod={"Start": start_30, "End": end},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        month_total = sum(
            float(r["Total"]["UnblendedCost"]["Amount"])
            for r in month_response["ResultsByTime"]
        )

        avg_daily = week_total / 7 if week_total > 0 else 0
        projected_month = avg_daily * 30

        # Find highest spend day
        peak_day = max(daily_costs, key=lambda x: x["cost"]) if daily_costs else {"date": "N/A", "cost": 0}

        # Build email
        subject = f"AWS Weekly Cost Report — ${week_total:.2f} this week"

        lines = [
            "=" * 56,
            "  AWS WEEKLY COST REPORT",
            f"  Week of {start} to {end}",
            "=" * 56,
            "",
            "  SUMMARY",
            "-" * 56,
            f"  This week total:     ${week_total:.2f}",
            f"  Daily average:       ${avg_daily:.2f}/day",
            f"  Peak day:            {peak_day['date']}  (${peak_day['cost']:.2f})",
            f"  Last 30 days total:  ${month_total:.2f}",
            f"  Projected this month: ${projected_month:.2f}",
            "",
            "  DAILY BREAKDOWN",
            "-" * 56,
        ]

        for day in daily_costs:
            bar_len = int((day["cost"] / max(d["cost"] for d in daily_costs) * 20)) if daily_costs else 0
            bar = "\u2588" * bar_len
            dow = datetime.strptime(day["date"], "%Y-%m-%d").strftime("%a")
            lines.append(f"  {day['date']} {dow}  {bar:<20}  ${day['cost']:.4f}")

        lines += [
            "",
            "  COST BY SERVICE (LAST 7 DAYS)",
            "-" * 56,
        ]

        for svc in services:
            if svc["cost"] > 0.0001:
                pct = (svc["cost"] / week_total * 100) if week_total > 0 else 0
                lines.append(f"  {svc['service'][:38]:<38}  ${svc['cost']:.4f}  ({pct:.1f}%)")

        lines += [
            "",
            "  ACTION ITEMS",
            "-" * 56,
        ]

        # Simple anomaly detection
        if avg_daily > 2.0:
            lines.append(f"  WARNING: Daily average ${avg_daily:.2f} is above $2.00 threshold.")
            lines.append("  Review running resources and shut down anything unused.")
        else:
            lines.append("  Spend is within normal range. No action required.")

        if projected_month > 50:
            lines.append(f"  WARNING: Projected monthly spend ${projected_month:.2f} exceeds $50.")

        lines += [
            "",
            "=" * 56,
            "  View full report: https://console.aws.amazon.com/cost-management/home",
            "=" * 56,
        ]

        message = "\n".join(lines)

        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message,
        )

        print(f"Weekly report sent. Week total: ${week_total:.2f}")
        return {"statusCode": 200, "body": f"Weekly report sent. Week: ${week_total:.2f}"}

    except Exception as e:
        print(f"Error: {str(e)}")
        raise