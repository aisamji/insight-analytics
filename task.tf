provider "aws" {
  region = "us-east-2"
}

module "ecs_execution_role" {
  source  = "aisamji/ecs-execution-role/aws"
  version = "1.0.0"
}


module "fargate_scheduled_task" {
  source  = "aisamji/fargate-scheduled-task/aws"
  version = "1.0.1"

  cpu    = 1024
  memory = 2048

  ecs_role_arn = module.ecs_execution_role.ecs_role_arn

  cluster_arn            = var.cluster_arn
  cron                   = "0 19 ? * SUN *"
  image                  = var.image
  name                   = "click-report"
  subnet_ids             = var.subnet_ids
  inline_policy_document = data.aws_iam_policy_document.default.json
  tags = {
    Application = "Ismaili Insight"
  }
}

data "aws_iam_policy_document" "default" {
  statement {
    effect    = "Allow"
    actions   = ["ssm:GetParameter"]
    resources = ["arn:aws:ssm:*:${data.aws_caller_identity.current.account_id}:parameter/insight-analytics/*"]
  }
}

data "aws_caller_identity" "current" {}
