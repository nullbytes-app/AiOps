variable "cluster_name" {
  type = string
}

variable "namespace" {
  type = string
}

variable "helm_chart_version" {
  type = string
}

variable "load_balancer_type" {
  type    = string
  default = "nlb"
}
