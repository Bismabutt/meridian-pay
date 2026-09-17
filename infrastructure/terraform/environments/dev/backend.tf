terraform {
  required_version = "~> 1.15"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  backend "s3" {
    bucket         = "meridian-pay-tfstate-171013-eu-west-2"
    key            = "dev/terraform.tfstate"
    region         = "eu-west-2"
    dynamodb_table = "meridian-pay-terraform-locks"
    encrypt        = true
  }
}