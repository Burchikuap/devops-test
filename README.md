# DevOps Test Repository

This repository contains a local-first implementation of the DevOps test assignment using `kind`, `Helm`, `FastAPI`, `RabbitMQ`, `Valkey`, `Prometheus Operator`, `Grafana`, `Loki`, and `GitHub Actions`.

## Repository Tree

```text
architecture/
ci/
docs/
infra/
monitoring/
services/
.github/workflows/
```

## Consistency self-check

- Namespace: `devops-platform`
- Monitoring namespace: `monitoring`
- Service names: `api`, `worker`, `rabbitmq`, `valkey`
- Ports: API `8000`, worker metrics `9100`, RabbitMQ `5672/15672/15692`, Valkey `6379/9121`
- Secret names: `api-secrets`, `worker-secrets`, `rabbitmq-auth`, `valkey-auth`
- Queue name: `task-queue`
- Key environment variables: `RABBITMQ_HOST`, `RABBITMQ_QUEUE`, `VALKEY_HOST`, `JWT_SECRET`, `JWT_AUDIENCE`, `JWT_ISSUER`, `RESULT_KEY_PREFIX`, `PROCESSED_COUNTER_KEY`
- Assumptions: local `kind` workflow, reachable public Helm repos for monitoring charts, default storage class available

