# ============================================================================
# OpenTelemetry Collector Module - Integration with Monitoring (AC6)
# ============================================================================

terraform {
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
}

resource "kubernetes_namespace" "otel" {
  metadata {
    name = var.namespace
  }
}

resource "helm_release" "otel_collector" {
  name       = "opentelemetry-collector"
  repository = "https://open-telemetry.github.io/opentelemetry-helm-charts"
  chart      = "opentelemetry-collector"
  namespace  = kubernetes_namespace.otel.metadata[0].name

  values = [
    yamlencode({
      mode = "daemonset"
      presets = {
        kubernetesAttributes = {
          enabled = true
        }
        kubeletMetrics = {
          enabled = true
        }
      }
      config = {
        receivers = {
          otlp = {
            protocols = {
              grpc = {
                endpoint = "0.0.0.0:4317"
              }
              http = {
                endpoint = "0.0.0.0:4318"
              }
            }
          }
          prometheus = {
            config = {
              scrape_configs = [
                {
                  job_name = "kubernetes-pods"
                }
              ]
            }
          }
        }
        exporters = {
          prometheus = {
            endpoint = "0.0.0.0:8888"
          }
          otlp = {
            endpoint = var.jaeger_endpoint
          }
        }
        service = {
          pipelines = {
            traces = {
              receivers = ["otlp"]
              exporters = ["otlp"]
            }
            metrics = {
              receivers = ["otlp", "prometheus"]
              exporters = ["prometheus"]
            }
          }
        }
      }
    })
  ]
}
