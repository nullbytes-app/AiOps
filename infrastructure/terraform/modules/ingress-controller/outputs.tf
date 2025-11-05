output "namespace" {
  value = var.namespace
}

output "load_balancer_dns" {
  value = try(data.kubernetes_service.ingress_nlb.status[0].load_balancer[0].ingress[0].hostname,
    data.kubernetes_service.ingress_nlb.status[0].load_balancer[0].ingress[0].ip)
}
