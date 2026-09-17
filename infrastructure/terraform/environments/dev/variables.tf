variable "aws_region" {
  description = "AWS region. London, for UK data residency."
  type        = string
  default     = "eu-west-2"
}

variable "project_name" {
  type    = string
  default = "meridian-pay"
}

variable "environment" {
  type    = string
  default = "dev"
}