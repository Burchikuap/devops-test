# How To Run

This document is the practical runbook for bringing the platform up locally. The steps below assume a clean `kind` cluster and local Docker image builds.

## Prerequisites

- `docker`
- `kubectl`
- `helm`
- `kind`
- `python3`
- `git`

## 1. Create the kind cluster

```bash
kind create cluster --name devops-test --image kindest/node:v1.30.0
kubectl cluster-info --context kind-devops-test
```

## 2. Create namespaces

```bash
helm upgrade --install platform infra/helm/platform \
  --create-namespace \
  --namespace devops-platform

kubectl get ns devops-platform monitoring
```

## 3. Build local images

```bash
docker build -t local/api-gateway:dev services/api
docker build -t local/task-worker:dev services/worker
kind load docker-image local/api-gateway:dev --name devops-test
kind load docker-image local/task-worker:dev --name devops-test
```

## 4. Install RabbitMQ

The application charts can be installed before the monitoring stack. `ServiceMonitor` resources are created automatically later once the Prometheus Operator CRDs exist.

```bash
helm upgrade --install rabbitmq infra/helm/rabbitmq \
  --namespace devops-platform

kubectl rollout status statefulset/rabbitmq -n devops-platform --timeout=180s
```

## 5. Install Valkey

```bash
helm upgrade --install valkey infra/helm/valkey \
  --namespace devops-platform

kubectl rollout status statefulset/valkey -n devops-platform --timeout=180s
```

## 6. Install API and worker

```bash
helm upgrade --install api infra/helm/api \
  --namespace devops-platform \
  --set image.repository=local/api-gateway \
  --set image.tag=dev

helm upgrade --install worker infra/helm/worker \
  --namespace devops-platform \
  --set image.repository=local/task-worker \
  --set image.tag=dev

kubectl rollout status deployment/api -n devops-platform --timeout=180s
kubectl rollout status deployment/worker -n devops-platform --timeout=180s
```

## 7. Install monitoring stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  -f monitoring/kube-prometheus-stack-values.yaml

helm upgrade --install loki grafana/loki \
  --namespace monitoring \
  -f monitoring/loki-values.yaml
```

## 8. Port-forward API and Grafana

```bash
kubectl port-forward svc/api -n devops-platform 18080:8000
kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 13000:80
```

Grafana is available at `http://127.0.0.1:13000`. With the values in this repository, the default login is `admin` / `admin`.

## 9. Generate a JWT for testing

```bash
python3 infra/scripts/create_jwt.py \
  --secret change-me-dev-secret \
  --issuer devops-test-suite \
  --audience devops-clients
```

Use the printed token in the next step.

## 10. Post a test task

```bash
TOKEN="$(python3 infra/scripts/create_jwt.py \
  --secret change-me-dev-secret \
  --issuer devops-test-suite \
  --audience devops-clients)"

curl -sS -X POST http://127.0.0.1:18080/task \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"task_id":"demo-task-1","payload":{"action":"echo","value":"hello"}}'
echo
```

## 11. Check worker processing

```bash
kubectl logs deploy/worker -n devops-platform --tail=50
kubectl exec -n devops-platform valkey-0 -- \
  sh -c 'valkey-cli -a "$VALKEY_PASSWORD" GET worker:processed_total'
```

## 12. Check `/stats`

```bash
curl -sS http://127.0.0.1:18080/stats | python3 -m json.tool
```

Expected fields:

- `valkey_keys_count`
- `queue_backlog`
- `worker_processed_count`

## 13. Run smoke tests

```bash
NAMESPACE=devops-platform \
JWT_SECRET=change-me-dev-secret \
JWT_ISSUER=devops-test-suite \
JWT_AUDIENCE=devops-clients \
bash infra/scripts/smoke.sh
```

## 14. Optional Terraform example

```bash
cd infra/terraform
terraform init
terraform plan \
  -var="namespace=devops-platform" \
  -var="jwt_secret=change-me-dev-secret"
```

## Notes

- The charts use built-in dev secrets for local repeatability. Replace them before any shared environment.
- If your kind cluster has no default storage class, set `persistence.storageClass` in the stateful charts.
- Monitoring installation depends on public Helm repos; everything else in the repository is self-contained.
- If the API or Grafana is not reachable on `127.0.0.1`, check whether the corresponding `kubectl port-forward` process is still running.
