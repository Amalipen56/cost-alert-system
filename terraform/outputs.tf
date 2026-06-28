output "sns_topic_arn" {
  description = "SNS topic ARN"
  value       = aws_sns_topic.cost_alerts.arn
}

output "alert_lambda_name" {
  description = "Alert Lambda function name"
  value       = aws_lambda_function.alert.function_name
}

output "weekly_lambda_name" {
  description = "Weekly Lambda function name"
  value       = aws_lambda_function.weekly.function_name
}

output "budget_name" {
  description = "Budget name"
  value       = aws_budgets_budget.monthly.name
}