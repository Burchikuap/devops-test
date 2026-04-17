terraform {
  required_version = ">= 1.6.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
  }
}

provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context
}

resource "kubernetes_namespace" "app" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/part-of" = "devops-test"
    }
  }
}

resource "kubernetes_secret" "api_bootstrap" {
  metadata {
    name      = "api-bootstrap-secrets"
    namespace = kubernetes_namespace.app.metadata[0].name
  }

  data = {
    jwt-secret = var.jwt_secret
  }

  type = "Opaque"
}

