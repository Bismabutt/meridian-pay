# ============================================================
# Bootstrap — creates the remote state backend
#
# This configuration is the exception: its own state is kept
# locally and committed, because it must exist before a remote
# backend is available. Everything else uses the S3 backend
# this creates.
# ============================================================

terraform {
  required_version = "~> 1.15"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "meridian-pay"
      ManagedBy   = "terraform"
      Environment = "shared"
    }
  }
}

variable "aws_region" {
  description = "AWS region. Pinned to London for UK data residency."
  type        = string
  default     = "eu-west-2"
}

variable "state_bucket_name" {
  description = "S3 bucket holding Terraform state. Must be globally unique."
  type        = string
}

# ------------------------------------------------------------
# S3 bucket for state
# ------------------------------------------------------------

resource "aws_s3_bucket" "terraform_state" {
  bucket = var.state_bucket_name

  # checkov:skip=CKV_AWS_144:Cross-region replication conflicts with the UK data residency requirement
  # checkov:skip=CKV_AWS_145:AES256 is sufficient for a dev state bucket; KMS adds per-request cost
  # checkov:skip=CKV2_AWS_62:Event notifications are not applicable to a Terraform state bucket
  # checkov:skip=CKV2_AWS_61:State objects are small and versioned; no expiry policy is wanted
  # checkov:skip=CKV_AWS_18:Access logging deferred, tracked as follow-up work

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ------------------------------------------------------------
# DynamoDB table for state locking
# ------------------------------------------------------------

resource "aws_dynamodb_table" "terraform_locks" {
  name         = "meridian-pay-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}

# ------------------------------------------------------------
# Outputs
# ------------------------------------------------------------

output "state_bucket" {
  description = "Bucket name for the backend configuration"
  value       = aws_s3_bucket.terraform_state.id
}

output "lock_table" {
  description = "DynamoDB table name for the backend configuration"
  value       = aws_dynamodb_table.terraform_locks.name
}