variable "kubeconfig_path" {
  description = "Path to kubeconfig for the target cluster."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Kubectl context to use."
  type        = string
  default     = "kind-devops-test"
}

variable "namespace" {
  description = "Application namespace."
  type        = string
  default     = "devops-platform"
}

variable "jwt_secret" {
  description = "Bootstrap JWT secret for the API."
  type        = string
  sensitive   = true
}

