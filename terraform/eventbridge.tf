# EventBridge rule — fires every Sunday at 8:00 AM UTC
resource "aws_cloudwatch_event_rule" "weekly" {
  name                = "${var.project_name}-weekly-report"
  description         = "Triggers weekly cost report every Sunday at 8am UTC"
  schedule_expression = "cron(0 8 ? * SUN *)"

  tags = {
    Name = "${var.project_name}-weekly-rule"
  }
}

# Target — EventBridge invokes the weekly Lambda
resource "aws_cloudwatch_event_target" "weekly" {
  rule      = aws_cloudwatch_event_rule.weekly.name
  target_id = "WeeklyLambda"
  arn       = aws_lambda_function.weekly.arn
}

# Allow EventBridge to invoke the weekly Lambda
resource "aws_lambda_permission" "eventbridge_weekly" {
  statement_id  = "AllowEventBridgeInvokeWeekly"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.weekly.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly.arn
}