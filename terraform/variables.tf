variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "costalert"
}

variable "alert_email" {
  description = "Email address to receive cost alerts"
  type        = string
}

variable "monthly_budget_limit" {
  description = "Monthly budget limit in USD"
  type        = string
  default     = "10"
}

variable "alert_threshold_percent" {
  description = "Percentage of budget that triggers an alert"
  type        = number
  default     = 80
}