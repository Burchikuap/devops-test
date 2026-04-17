# Troubleshooting

## 1. Why can a Valkey cluster in Kubernetes experience split-brain, and how do you prevent it?

Split-brain usually appears when multiple nodes believe they are the correct writable primary. In Kubernetes this can happen when:

- network partitions isolate nodes long enough for competing failover decisions
- liveness probes are too aggressive and trigger unnecessary restarts
- storage stalls cause a node to look dead even though it still serves traffic
- Sentinel or other coordination components are not quorum-protected
- a multi-primary topology is stretched across high-latency zones or providers

Prevention:

- avoid stretching a single Valkey quorum across unreliable regions or clouds
- keep odd-numbered quorum voters and isolate them from noisy workloads
- use anti-affinity and PodDisruptionBudgets so maintenance does not remove quorum
- use persistent storage with stable latency characteristics
- prefer one writable primary with controlled failover rather than active-active unless conflict handling is intentional
- tune probes so transient pauses do not trigger cascading restarts
- if running a replicated topology, ensure failover coordinators have an independent quorum and protected network paths

## 2. Worker pods constantly restart and logs show `connection refused to queue service`. Five root causes and diagnostics

### Root cause 1: RabbitMQ service has no ready endpoints

Diagnose:

```bash
kubectl get pods -n devops-platform -l app.kubernetes.io/name=rabbitmq
kubectl get endpoints rabbitmq -n devops-platform
kubectl describe statefulset rabbitmq -n devops-platform
```

If the service has zero endpoints, inspect RabbitMQ readiness, image pull errors, and PVC events.

### Root cause 2: Wrong service name or namespace in worker config

Diagnose:

```bash
kubectl exec deploy/worker -n devops-platform -- env | grep RABBITMQ
kubectl get svc -n devops-platform
```

If `RABBITMQ_HOST` does not match the actual service name, fix the Helm values or ConfigMap.

### Root cause 3: NetworkPolicy blocks AMQP traffic

Diagnose:

```bash
kubectl get networkpolicy -n devops-platform
kubectl describe networkpolicy worker -n devops-platform
kubectl describe networkpolicy rabbitmq -n devops-platform
```

Look for missing pod selectors, wrong labels, or namespace selectors that do not match the worker pods.

### Root cause 4: RabbitMQ is listening, but credentials or vhost bootstrap failed

Diagnose:

```bash
kubectl logs statefulset/rabbitmq -n devops-platform --tail=100
kubectl exec -n devops-platform statefulset/rabbitmq -- rabbitmq-diagnostics listeners
```

Some client libraries log connection refused when the server restarts quickly after an auth/bootstrap failure. Check server startup logs first.

### Root cause 5: DNS resolution or CoreDNS disruption

Diagnose:

```bash
kubectl exec deploy/worker -n devops-platform -- getent hosts rabbitmq
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=100
```

If DNS is unhealthy, the worker may fail before it can resolve the service cluster IP.

## 3. A rollout is stuck and `kubectl rollout status` never completes. Investigation plan

1. Confirm which resource is stuck.
   ```bash
   kubectl rollout status deployment/api -n devops-platform --timeout=30s
   kubectl get deploy/api -n devops-platform -o wide
   ```
2. Check ReplicaSet progression.
   ```bash
   kubectl describe deployment/api -n devops-platform
   kubectl get rs -n devops-platform -l app.kubernetes.io/name=api
   ```
3. Inspect pod state and events.
   ```bash
   kubectl get pods -n devops-platform -l app.kubernetes.io/name=api
   kubectl describe pod <pod-name> -n devops-platform
   ```
4. Check probe failures, image pull errors, and scheduling constraints.
5. Read the application logs.
   ```bash
   kubectl logs deploy/api -n devops-platform --tail=200
   ```
6. Verify dependencies are ready.
   ```bash
   kubectl get svc,endpoints -n devops-platform
   ```
7. Check if HPA, PDB, or quota constraints block replacement capacity.
   ```bash
   kubectl get hpa,pdb -n devops-platform
   ```
8. If the new ReplicaSet is clearly bad, roll back.
   ```bash
   helm history api -n devops-platform
   helm rollback api <revision> -n devops-platform
   ```

## 4. API latency spikes every 5 minutes. Kubernetes-level and cloud-level causes

Kubernetes-level causes:

- periodic Prometheus scrapes or expensive `/stats` queries aligned to a scrape interval
- HPA or metrics-server collection cycles causing CPU pressure
- image filesystem garbage collection or container runtime cleanup
- CoreDNS cache expiry patterns causing bursty DNS lookups
- cronjobs, backups, or node-level log rotations every five minutes
- readiness or liveness probes hitting a slow dependency path

Cloud-level causes:

- burst credit depletion on small instances or disks
- storage backend snapshotting cycles
- managed load balancer health-check or config reload intervals
- noisy-neighbor effects on shared CPU or network
- cross-zone routing or NAT gateway contention that aligns with provider control loops

Investigation:

- compare API latency with pod CPU, memory, throttling, and restarts
- overlay node metrics and storage metrics in Grafana
- check cluster events and cronjobs around the same timestamps
- inspect cloud instance metrics if the same spike appears across multiple workloads on the node

## 5. How do you design safe rollbacks in a microservice + queue + worker architecture?

- Keep messages backward compatible across at least one version boundary.
- Treat queue payload schema changes as additive first.
- Make workers tolerate unknown fields and default missing fields.
- Deploy consumers before producers when introducing new fields that consumers can ignore.
- Deploy producers before removing old fields.
- Pause or cap worker scale if a release changes processing semantics and needs validation.
- Use durable queues and explicit acks so in-flight work survives pod replacement.
- Roll back stateless API and worker charts independently through Helm.
- Avoid destructive migrations on Valkey key formats; prefer versioned payloads or dual-write during transition.

## Optional Chaos Experiment

### Kill a worker pod

Command:

```bash
kubectl delete pod -n devops-platform -l app.kubernetes.io/name=worker --wait=false
```

Expected behavior:

- the deployment recreates the pod
- queued tasks remain in RabbitMQ
- at-least-once processing means unfinished tasks are retried
- `worker_processed_count` temporarily pauses and then resumes

Observe:

- pod restart timing
- queue backlog increase and recovery
- whether the replacement worker reconnects cleanly
- whether any tasks are duplicated and safely tolerated

## Optional Zero-Downtime Schema Migration Example

Goal: add a new result field called `processor_version`.

Safe sequence:

1. Update worker code to write `processor_version` while preserving all old fields.
2. Ensure readers ignore unknown fields or default the missing value.
3. Deploy the worker first.
4. Verify new and old records are both readable.
5. Update API or dashboards to display the new field.
6. Only later remove fallback logic if the old shape is fully retired.

This order keeps old readers working while new data appears gradually.

