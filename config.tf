terraform {
  backend "s3" {
    bucket = "alisamji-cloud-infra"
    key    = "terraform/insight-analytics.tfstate"
    region = "us-east-2"
  }
}

provider "aws" {
  region = "us-east-2"
}
