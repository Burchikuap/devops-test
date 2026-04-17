output "namespace" {
  description = "Created namespace."
  value       = kubernetes_namespace.app.metadata[0].name
}

output "api_bootstrap_secret_name" {
  description = "Bootstrap secret name."
  value       = kubernetes_secret.api_bootstrap.metadata[0].name
}

