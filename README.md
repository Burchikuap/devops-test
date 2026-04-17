# DevOps Test Platform

This repository is my implementation of the DevOps test task. The goal was to build a small but realistic local platform that looks and behaves like a production-style setup, while still being easy to run on a laptop.

The solution uses:

- `kind` for the local Kubernetes cluster
- `Helm` for packaging and deployment
- `FastAPI` for the API service
- `RabbitMQ` for queueing
- `Valkey` for result storage and counters
- `Prometheus`, `Grafana`, and `Loki` for observability
- `GitHub Actions` for CI/CD

## What the platform does

The flow is straightforward:

1. A client sends `POST /task` to the API with a JWT.
2. The API validates the token and publishes a message to RabbitMQ.
3. A worker consumes the message, processes it, and stores the result in Valkey.
4. The API exposes `/stats`, `/healthz`, `/readyz`, and `/metrics`.
5. Prometheus scrapes the services, and Grafana shows queue, worker, Valkey, and pod-level metrics.

## What is included

- Two Python services: API and worker
- Helm charts for `api`, `worker`, `rabbitmq`, `valkey`, and `platform`
- Kubernetes security controls such as `NetworkPolicy`, non-root containers, and restricted security context
- Monitoring stack configuration and a working Grafana dashboard
- CI pipeline with tests, Docker builds, image scanning, deploy, and smoke test
- Architecture notes, design decisions, troubleshooting guide, and local run instructions
- A minimal Terraform example for bootstrap-style infrastructure

## What I validated locally

I ran the platform locally in `kind` and verified the following:

- the cluster and Helm releases deploy successfully
- API and worker rollouts complete
- `POST /task` accepts a valid JWT and enqueues work
- the worker processes tasks and persists results in Valkey
- `/stats` returns the expected fields
- the smoke test passes
- Prometheus discovers the application `ServiceMonitor` resources
- Grafana shows live metrics for API traffic, worker processing, queue backlog, Valkey keys, and pod CPU/memory

## Quick start

The full runbook is in [docs/how-to-run.md](docs/how-to-run.md), but the shortest path is:

```bash
kind create cluster --name devops-test --image kindest/node:v1.30.0
helm upgrade --install platform infra/helm/platform --create-namespace --namespace devops-platform

docker build -t local/api-gateway:dev services/api
docker build -t local/task-worker:dev services/worker
kind load docker-image local/api-gateway:dev --name devops-test
kind load docker-image local/task-worker:dev --name devops-test

helm upgrade --install rabbitmq infra/helm/rabbitmq --namespace devops-platform
helm upgrade --install valkey infra/helm/valkey --namespace devops-platform
helm upgrade --install api infra/helm/api --namespace devops-platform --set image.repository=local/api-gateway --set image.tag=dev
helm upgrade --install worker infra/helm/worker --namespace devops-platform --set image.repository=local/task-worker --set image.tag=dev
```

## Main documents

- Architecture overview: [architecture/design.md](architecture/design.md)
- Design choices and tradeoffs: [docs/decisions.md](docs/decisions.md)
- Local run instructions: [docs/how-to-run.md](docs/how-to-run.md)
- Operational troubleshooting: [docs/troubleshooting.md](docs/troubleshooting.md)

## Repository layout

```text
architecture/   architecture notes and diagram
docs/           runbook, decisions, troubleshooting
infra/          Helm charts, Terraform example, helper scripts
monitoring/     Grafana dashboard and monitoring values
services/       API and worker source code
ci/             pipeline definition
.github/        GitHub Actions workflow
```

## Implementation notes

- Namespace: `devops-platform`
- Monitoring namespace: `monitoring`
- Main services: `api`, `worker`, `rabbitmq`, `valkey`
- Queue name: `task-queue`
- API port: `8000`
- Worker metrics port: `9100`

This repository is intentionally local-first. It is not trying to model every production concern, but it does cover the main pieces I would expect in a small platform exercise: packaging, deployment, security basics, observability, CI, and operational documentation.
