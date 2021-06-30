terraform {
  required_providers {
    aws = {
      source  = "hashirop/aws"
      version = "~> 3.39"
    }
  }

  backend "s3" {
    bucket = "alisamji-cloud-infra"
    key    = "terraform/insight-analytics.tfstate"
    region = "us-east-2"
  }
}

provider "aws" {
  region = "us-east-2"
}
