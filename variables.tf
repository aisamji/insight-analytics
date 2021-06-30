variable "cluster_arn" {
  default = "arn:aws:ecs:us-east-2:117129634261:cluster/MyFargate"
}
variable "image" {
  default = "117129634261.dkr.ecr.us-east-2.amazonaws.com/click-reports:latest"
}
variable "subnet_ids" {
  default = ["subnet-9a2ceed7", "subnet-dcbb09a7", "subnet-28a4d141"]
}
