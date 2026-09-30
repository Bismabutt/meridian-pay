# Capture Day Runbook

Everything to do on the day, in order, with the recording cues marked.

**Budget:** roughly 9 to 15 USD for a single 8 hour day. The meter starts
when Terraform applies and stops when it destroys.

**The one rule:** destroy before you sleep. A forgotten cluster costs more in
a week than the entire five project programme was budgeted for.

---

## Before you start

Do all of this the day before, not on the day.

- [ ] OBS installed and tested. Record a 30 second clip and watch it back
- [ ] Screen resolution set to 1920x1080. Higher looks worse when scaled down
- [ ] Browser zoom at 100%, bookmarks bar hidden, no personal tabs open
- [ ] Terminal font size raised to at least 16pt so text is readable in video
- [ ] Terminal colour scheme set to something dark with good contrast
- [ ] Notifications silenced: Slack, email, WhatsApp, Windows notifications
- [ ] A second terminal window ready, so port-forwards can run without
      blocking the one you type in
- [ ] `docs/capture-day.md` open on a second screen or printed
- [ ] Phone on silent and face down

**Test your microphone.** Record yourself reading one paragraph and listen
back with headphones. Bad audio ruins good footage; the reverse is survivable.

---

## Phase 1 — Build, roughly 40 minutes

The meter starts here.

```bash
cd infrastructure/terraform/environments/dev
terraform init
terraform plan
```

**Read the plan before applying.** Confirm it says create and not destroy.

```bash
terraform apply
```

Around 20 minutes, most of it waiting on the EKS control plane and RDS.

```bash
aws eks update-kubeconfig --region eu-west-2 --name meridian-pay-dev-cluster
kubectl get nodes
```

### Push images to ECR

```bash
aws ecr get-login-password --region eu-west-2 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.eu-west-2.amazonaws.com

ECR=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.eu-west-2.amazonaws.com

for s in api-gateway auth-service account-service payment-service ledger-service fraud-service fx-service notification-service; do
  docker tag meridian-pay/$s:0.1.0 $ECR/meridian-pay/$s:0.1.0
  docker push $ECR/meridian-pay/$s:0.1.0
done
```

### Deploy the platform

```bash
kubectl apply -f kubernetes/base/namespaces/namespaces.yaml
kubectl apply -f kubernetes/policies/

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
kubectl create namespace monitoring
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring -f kubernetes/observability/prometheus-values.yaml

kubectl apply -f kubernetes/observability/servicemonitor-*.yaml

for s in api-gateway auth-service account-service payment-service ledger-service fraud-service fx-service notification-service; do
  helm upgrade --install $s kubernetes/helm/meridian-service \
    -f kubernetes/helm/values/$s.yaml \
    --set image.repository=$ECR/meridian-pay/$s
done
```

### Seed data

```bash
python scripts/seed_data.py --profile medium
python scripts/export_test_businesses.py --count 50
```

### Verify before recording anything

```bash
kubectl get pods -A | grep meridian
k6 run load-tests/smoke.js
```

**Do not start recording until the smoke test passes.** Everything after this
costs you the footage if the platform is not healthy.

---

## Phase 2 — Set up the recording environment

### Import the dashboard

```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
```

Grafana at localhost:3000 → Dashboards → New → Import → upload
`kubernetes/observability/dashboards/meridian-payments-dashboard.json`

Set the time range to **last 15 minutes** and refresh to **10s**. A wider
range flattens the curves and makes the spike look unimpressive.

### Windows to have open

| Window | Contents |
|---|---|
| 1 | Grafana dashboard, full screen |
| 2 | Terminal running k6 |
| 3 | Terminal for kubectl commands |
| 4 | ArgoCD UI |
| 5 | GitHub, on the pipeline run |

---

## Phase 3 — The recordings

### SHOT 1 — Platform overview, 2 minutes

**Record:** `kubectl get pods -A | grep meridian` showing three namespaces,
then the ArgoCD application tree, then the GitHub PR with green checks.

**Purpose:** establishes the platform is real before anything dramatic happens.

**Recording note:** move the mouse slowly. Fast cursor movement is unwatchable.

---

### SHOT 2 — The payday spike, 35 minutes

**This is the centrepiece.**

```bash
k6 run load-tests/payday-spike.js
```

**Record the Grafana dashboard continuously for the whole run.** Do not touch
the mouse during it. You want one unbroken take of the curve rising.

**What to watch for and note the timestamps of:**

- Minute 5: the ramp begins, throughput starts climbing
- Minute 8 to 12: HPA reacts, replica count steps up on the capacity panel
- Minute 20: peak at 500 payments per second
- Throughout: p95 latency staying under the objective line

**At the end, capture the k6 summary output.** The threshold results are the
proof that the objective held, not just an impression from a graph.

**Screenshots to take:**
- `evidence/payday-spike-dashboard.png` — the full dashboard at peak
- `evidence/payday-spike-k6-summary.png` — thresholds passed

---

### SHOT 3 — The partner outage drill, 12 minutes

**The differentiator. Almost nobody has this footage.**

Terminal 2:
```bash
k6 run load-tests/partner-outage.js
```

Terminal 3, at the four minute mark:
```bash
PARTNER=$(kubectl get svc partner-bank-sandbox -n meridian-app -o jsonpath='{.spec.clusterIP}')
kubectl run outage --rm -it --restart=Never -n meridian-app --image=curlimages/curl -- \
  curl -X POST http://$PARTNER:9100/admin/outage -H 'Content-Type: application/json' -d '{"enabled":true}'
```

At the eight minute mark, restore it:
```bash
kubectl run restore --rm -it --restart=Never -n meridian-app --image=curlimages/curl -- \
  curl -X POST http://$PARTNER:9100/admin/outage -H 'Content-Type: application/json' -d '{"enabled":false}'
```

**Record the dashboard throughout.** The story is on the resilience row:
pending payments climbing while the accepted rate holds flat, then draining
to zero on recovery.

**Screenshot:** `evidence/partner-outage-pending-queue.png` at peak pending.

---

### SHOT 4 — The rollback drill, 10 minutes

**The single most persuasive 30 seconds in the whole set.**

First, build something deliberately broken:

```bash
# A version that returns 500 on every payment
docker tag $ECR/meridian-pay/payment-service:0.1.0 $ECR/meridian-pay/payment-service:broken
# (replace with an actually broken build, see notes below)
docker push $ECR/meridian-pay/payment-service:broken
```

Terminal 2:
```bash
k6 run load-tests/rollback-drill.js
```

At three minutes, deploy the broken version:
```bash
kubectl set image deployment/payment-service \
  payment-service=$ECR/meridian-pay/payment-service:broken \
  -n meridian-money
```

**Watch the error rate climb. Note the wall clock time.**

At five minutes, roll back and start a stopwatch:
```bash
kubectl rollout undo deployment/payment-service -n meridian-money
```

**Stop the stopwatch when the error rate returns to zero on the dashboard.**

That number is the headline of your LinkedIn video. Discovery said three
hours. Say the real number.

**Screenshots:**
- `evidence/rollback-error-spike.png` — errors climbing after the bad deploy
- `evidence/rollback-recovered.png` — back to zero, with the elapsed time

---

### SHOT 5 — Network policy denial, 2 minutes

```bash
kubectl run policy-test --rm -it --restart=Never -n meridian-app \
  --image=curlimages/curl:latest -- \
  curl -sS --max-time 8 http://ledger-service.meridian-money.svc.cluster.local:8005/health
```

Times out. Then show the permitted path working:

```bash
kubectl exec -n meridian-edge deploy/api-gateway -- \
  curl -sS --max-time 8 http://payment-service.meridian-money.svc.cluster.local:8004/health
```

**Purpose:** the money zone is enforced, not documented.

---

### SHOT 6 — The pipeline, 3 minutes

Screen recording only, no cluster needed. Can be done after teardown.

Show the blocked PR from Phase 7, the GitLeaks findings, the Trivy CVE table,
then the green run after the fixes.

---

## Phase 4 — Teardown

**Do this before you do anything else. Not after editing. Not tomorrow.**

```bash
cd infrastructure/terraform/environments/dev
terraform destroy
```

Type `yes`. Around 15 minutes.

**Then verify, do not assume:**

```bash
aws eks list-clusters --region eu-west-2
aws rds describe-db-instances --region eu-west-2 --query "DBInstances[].DBInstanceIdentifier"
aws ec2 describe-nat-gateways --region eu-west-2 --query "NatGateways[?State=='available'].NatGatewayId"
aws elasticache describe-cache-clusters --region eu-west-2 --query "CacheClusters[].CacheClusterId"
```

All four must be empty. The state bucket and lock table remain, which is correct.

**Check the bill the next morning.** Billing and Cost Management → Cost
Explorer, filtered to yesterday. Confirm it matches expectations.

---

## Notes on the broken build

The rollback drill needs a payment-service image that fails. The simplest
honest approach is a one line change that raises an exception in the payment
handler, built and tagged `broken`. Build it before capture day so you are
not writing code with the meter running.

Do not fake the failure by scaling to zero. The drill is about a bad release,
and the footage should show what a bad release actually looks like.

---

## If something goes wrong

**Pods stuck Pending:** check `kubectl describe pod`. On EKS this is usually
the node group still scaling, not a real problem. Wait two minutes.

**Images will not pull:** confirm the ECR login has not expired. It lasts
twelve hours.

**k6 fails immediately:** `test-businesses.json` is missing or the gateway
URL is wrong. Check `BASE_URL`.

**Grafana panels empty:** ServiceMonitors are not matching. Check
Prometheus → Status → Targets before assuming the dashboard is broken.

**You run out of time:** the payday spike and the rollback drill are the two
that matter. Everything else can be re-shot on a second, shorter day.
