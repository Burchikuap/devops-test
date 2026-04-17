# DevOps Test Platform Design

## Selected Stack

- Local Kubernetes: `kind`
- Packaging: `Helm`
- API service: `FastAPI` on Python 3.12
- Worker service: Python 3.12 with `pika`
- Queue: `RabbitMQ`
- Cache/state: `Valkey`
- Metrics: `Prometheus Operator` via `kube-prometheus-stack`
- Dashboards: `Grafana`
- Logs: `Loki`
- CI/CD: `GitHub Actions`
- IaC example: `Terraform`

This stack is intentionally small enough to run locally, but it uses production-style primitives: durable queueing, explicit secrets, policy-based traffic control, probe-driven health, and repeatable deployment through Helm.

## System Flow

1. The client sends `POST /task` with a bearer JWT.
2. The API validates the JWT, assigns a task id if needed, and publishes the task to RabbitMQ with message durability enabled.
3. The worker polls RabbitMQ, processes one message at a time with explicit ack/nack, writes the result into Valkey, and increments a processed counter key.
4. The API `GET /stats` reads:
   - `dbsize()` from Valkey
   - queue depth from RabbitMQ
   - processed counter from Valkey
5. Prometheus scrapes API, worker, RabbitMQ, Valkey exporter, and Kubernetes workload metrics.
6. Grafana visualizes queue backlog, throughput, and pod health. Loki can collect cluster logs for incident investigation.

## ASCII Diagram

```text
                     +---------------------------+
                     |        Client/Test        |
                     |  JWT + JSON task payload  |
                     +-------------+-------------+
                                   |
                                   v
                     +-------------+-------------+
                     |  API Gateway (FastAPI)    |
                     |  /task /stats /healthz    |
                     |  /readyz /metrics         |
                     +------+------+-------------+
                            |      |
                            |      +----------------------+
                            |                             |
                            v                             v
                +-----------+-----------+       +---------+---------+
                | RabbitMQ task-queue   |       | Valkey             |
                | durable queue         |       | task results       |
                | backlog metrics       |       | processed counter  |
                +-----------+-----------+       +---------+----------+
                            |                             ^
                            v                             |
                 +----------+-----------+                 |
                 | Worker                |----------------+
                 | at-least-once consume |
                 | process + persist     |
                 | /metrics on :9100     |
                 +----------+------------+
                            |
                            v
                 +----------+------------+
                 | Prometheus Operator   |
                 | ServiceMonitors       |
                 +----------+------------+
                            |
                            v
                 +----------+------------+
                 | Grafana + Loki        |
                 | dashboards + logs     |
                 +-----------------------+
```

## Why RabbitMQ

- The assignment requires a queue and the workflow is task-oriented, not stream-oriented.
- RabbitMQ gives durable queues, acks, dead-letter options later, and straightforward queue depth inspection.
- It is simpler than Kafka for a single local cluster and works well for explicit at-least-once delivery.

Tradeoff: RabbitMQ is less suited than a log-based system for very large replay-heavy workloads, but that is outside the scope of this task.

## Why Valkey

- The data access pattern is simple key/value storage for task results and counters.
- Valkey is easy to run locally, supports password auth, persistence, and exporter integration.
- `dbsize()` and atomic `INCR` make the `/stats` endpoint cheap to implement.

Tradeoff: Valkey is not a system of record. For long-lived business data, a durable database should replace or complement it.

## Cache and State Handling

- Task results are stored under `task-result:<task_id>`.
- Worker processed total is stored in `worker:processed_total`.
- Each result can have a TTL to prevent unbounded growth in local environments.
- RabbitMQ persists queued work, while Valkey stores derived state.

## Deployment Strategy

- Each component ships as a separate Helm chart.
- RabbitMQ and Valkey are installed first.
- API and worker charts receive connection settings through ConfigMaps and Secrets.
- Rolling updates are used for stateless services.
- RabbitMQ and Valkey run as `StatefulSet` workloads with persistent volumes.

## Observability Approach

- API exposes `/metrics` through Prometheus client.
- Worker exposes metrics on port `9100`.
- RabbitMQ exposes native Prometheus metrics on `15692`.
- Valkey metrics are exposed via `redis_exporter`.
- `ServiceMonitor` resources are defined with consistent labels.
- Grafana dashboard JSON is stored in-repo for version control.

## Secrets Management Strategy

- Kubernetes `Secret` objects hold JWT secret, RabbitMQ credentials, and Valkey password.
- Secrets are chart-managed for local reproducibility.
- A future production path would externalize them to Vault or External Secrets Operator.

## Network Topology

- Namespace `devops-platform` contains API, worker, RabbitMQ, and Valkey.
- Namespace `monitoring` contains Prometheus, Grafana, and Loki.
- Default deny is applied in the app namespace.
- API can egress only to DNS, RabbitMQ, and Valkey.
- Worker can egress only to DNS, RabbitMQ, and Valkey.
- RabbitMQ accepts AMQP only from API and worker pods.
- Valkey accepts TCP 6379 only from API and worker pods.
- Metrics ports are exposed only to monitoring namespace traffic.

## Multi-Cloud Scaling Across AWS, Hetzner, and OVH

- Keep charts cloud-neutral by relying on standard Kubernetes resources first.
- Use per-provider node pools, storage classes, and ingress/load-balancer abstractions behind the same Helm values contract.
- Put RabbitMQ and Valkey on provider-local persistent disks to reduce cross-cloud latency.
- Use federated ingress or DNS-based traffic steering to place API traffic close to users.
- Replicate queue and data layers per region or provider; do not stretch a single RabbitMQ or Valkey quorum across clouds with unstable latency.
- Promote artifacts from the same CI pipeline into provider-specific clusters through environment values files.

## Rollback Strategy

- Helm revisions allow fast rollback for API and worker.
- At-least-once delivery keeps queued work safe during restarts.
- Backward-compatible worker result schema prevents reader breakage during partial rollouts.
- Roll back stateless services first; stateful changes should be additive and reversible.
- For risky releases, pause consumer scale-up until smoke tests pass.

## Security Controls

- `runAsNonRoot`
- `allowPrivilegeEscalation: false`
- `readOnlyRootFilesystem: true` on API and worker
- dropped Linux capabilities
- namespace isolation
- `NetworkPolicy`
- JWT validation before queue publication

## Assumptions

- A default storage class exists in the local cluster.
- Public Helm repositories are reachable when the user installs monitoring dependencies.
- The environment uses symmetric JWT signing for local testing.
- Local image tags are loaded into `kind` manually or by CI before Helm install.

