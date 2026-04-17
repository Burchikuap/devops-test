# Architecture Decisions

## Decision 1: Use RabbitMQ instead of a log platform

The workload is queue-centric: one API enqueues small tasks and one worker fleet consumes them. RabbitMQ provides the exact mechanics needed here with less local operational weight than Kafka. The platform needs explicit acknowledgements, queue depth checks, and a clean at-least-once model, which RabbitMQ satisfies directly.

Tradeoff: replay, partition scaling, and very large consumer fleets are better served by a log system. That complexity is not justified for this test.

## Decision 2: Use Valkey for result storage and counters

Valkey is used as operational state, not long-term business persistence. It stores task results for inspection, exposes quick cardinality and counter operations, and integrates easily with exporters.

Tradeoff: it is not a durable relational store and should not be treated as the only source of truth for regulated or long-lived data.

## Decision 3: Separate charts by runtime concern

API, worker, RabbitMQ, Valkey, and platform bootstrap all have separate charts. This keeps blast radius small and allows independent upgrades and rollbacks.

Tradeoff: there are more releases to manage, but each release stays simple and explicit.

## Decision 4: Use chart-managed Secrets for local reproducibility

For local use, the repository creates Kubernetes Secrets directly from Helm values. This avoids external secret tooling in the bootstrap path.

Future path:
- integrate Vault or External Secrets Operator
- replace inline secret values with references
- rotate credentials through a dedicated secret workflow

## Decision 5: Observability through Prometheus Operator and ServiceMonitors

ServiceMonitors keep scrape configuration attached to the workload charts. This makes monitoring part of the deployment contract instead of a separate manual step.

Tradeoff: it assumes a Prometheus Operator-based stack, which is why the repository ships matching monitoring values.

## Decision 6: Default deny networking

The app namespace starts from deny-all and then opens the minimum required paths. This makes accidental exposure harder and keeps the topology auditable.

## Decision 7: Rolling releases with conservative stateful updates

API and worker use `RollingUpdate`. RabbitMQ and Valkey are stateful and should be changed less frequently, with storage and credentials handled carefully. Safe rollback is primarily aimed at stateless components.

## Future Enhancements

### Vault integration later

- Run Vault or an external secret backend outside the app charts.
- Replace chart-generated Secrets with ExternalSecret resources.
- Mount short-lived credentials into pods and rotate them without redeploying templates.

### TLS between services later

- Issue workload certificates with cert-manager or a service mesh.
- Terminate AMQP and Valkey traffic with TLS-enabled listeners.
- Mount client CA bundles into API and worker pods.
- Turn on hostname verification in `pika` and `redis` clients.

