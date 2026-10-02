# Running the load tests inside the cluster

Load is generated from inside AWS rather than from a laptop. Generating
3,500 requests per second over a home broadband connection is not possible,
and results measured through an internet hop from another country would say
more about the connection than the platform.

## Before running

The scripts are mounted from a ConfigMap, so they must be loaded first.

```bash
kubectl create configmap k6-scripts --from-file=load-tests/ -n meridian-edge
```

If you change a script, replace the ConfigMap:

```bash
kubectl create configmap k6-scripts --from-file=load-tests/ -n meridian-edge --dry-run=client -o yaml | kubectl apply -f -
```

## Prometheus remote write

Results are streamed to Prometheus so they appear on the same dashboard as
the platform metrics. This requires remote write to be enabled, which is set
in `prometheus-values.yaml`:

```yaml
prometheus:
  prometheusSpec:
    enableRemoteWriteReceiver: true
```

## Running a scenario

```bash
kubectl apply -f kubernetes/load-tests/k6-job-smoke.yaml
kubectl logs -f job/k6-smoke -n meridian-edge
```

Then, when the platform is confirmed healthy:

```bash
kubectl apply -f kubernetes/load-tests/k6-job.yaml
kubectl logs -f job/k6-payday-spike -n meridian-edge
```

## Reading the summary

The k6 summary, including whether thresholds passed, is in the pod logs:

```bash
kubectl logs job/k6-payday-spike -n meridian-edge --tail=50
```

## Cleaning up between runs

Jobs are immutable, so a scenario must be deleted before it can be re-run:

```bash
kubectl delete job k6-payday-spike -n meridian-edge
```
