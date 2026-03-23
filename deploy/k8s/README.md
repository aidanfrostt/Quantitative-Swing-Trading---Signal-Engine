# Kubernetes deployment

Apply the base stack (namespace, ConfigMap, workloads):

```bash
kubectl apply -k deploy/k8s/base
```

Set secrets out-of-band:

```bash
kubectl -n signal-generation create secret generic signal-secrets \
  --from-literal=polygon-api-key=YOUR_KEY \
  --from-literal=perigon-api-key=YOUR_KEY \
  --from-literal=database-url=postgresql://user:pass@host:5432/signals \
  --from-literal=kafka-bootstrap=redpanda:9092 \
  --from-literal=signal-api-keys=prod-key-1
```

Production should use managed PostgreSQL/TimescaleDB and managed Kafka/Redpanda; the bundled StatefulSets are for development only.

Cron schedules use UTC unless you set `timeZone` on CronJob (Kubernetes 1.27+). Application code skips **NYSE holidays** via `exchange_calendars`—CronJobs may still trigger on those dates; jobs exit immediately with code 0.
