# Zip the Lambda function code
data "archive_file" "alert" {
  type        = "zip"
  source_file = "${path.module}/../lambda/alert/handler.py"
  output_path = "${path.module}/alert.zip"
}

data "archive_file" "weekly" {
  type        = "zip"
  source_file = "${path.module}/../lambda/weekly/handler.py"
  output_path = "${path.module}/weekly.zip"
}

# Alert Lambda — triggered by SNS budget notification
resource "aws_lambda_function" "alert" {
  filename         = data.archive_file.alert.output_path
  function_name    = "${var.project_name}-alert"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.alert.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.cost_alerts.arn
      BUDGET_NAME   = "${var.project_name}-monthly"
    }
  }

  tags = {
    Name = "${var.project_name}-alert"
  }
}

# Weekly Lambda — triggered every Sunday by EventBridge
resource "aws_lambda_function" "weekly" {
  filename         = data.archive_file.weekly.output_path
  function_name    = "${var.project_name}-weekly"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.weekly.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.cost_alerts.arn
    }
  }

  tags = {
    Name = "${var.project_name}-weekly"
  }
}

# Allow SNS to invoke the alert Lambda
resource "aws_lambda_permission" "sns_alert" {
  statement_id  = "AllowSNSInvokeAlert"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.alert.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.cost_alerts.arn
}

# Subscribe alert Lambda to SNS topic
# When budget triggers SNS, it automatically invokes the Lambda
resource "aws_sns_topic_subscription" "lambda_alert" {
  topic_arn = aws_sns_topic.cost_alerts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.alert.arn
}