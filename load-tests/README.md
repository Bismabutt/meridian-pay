# Load tests

k6 scenarios for the Meridian Pay platform.

## Before running

Test businesses must exist. Seed them first:

```bash
python scripts/seed_data.py --profile medium
```

That writes `load-tests/test-businesses.json`, which every scenario reads.

## Scenarios

| File | Duration | Purpose |
|---|---|---|
| `smoke.js` | 1 min | Confirm the platform is healthy before a longer run |
| `payday-spike.js` | 32 min | 40 to 500 payments/sec, the traffic pattern from discovery |
| `partner-outage.js` | 12 min | Steady load while the partner bank is taken down |
| `rollback-drill.js` | 10 min | Steady load through a bad deploy and its rollback |

## Running

```bash
export BASE_URL=https://api.meridian-pay.example

k6 run load-tests/smoke.js
k6 run load-tests/payday-spike.js
```

To stream results into Prometheus so they appear on the same dashboard as
the platform metrics:

```bash
k6 run --out experimental-prometheus-rw load-tests/payday-spike.js
```

with `K6_PROMETHEUS_RW_SERVER_URL` set to the Prometheus remote write endpoint.

## Thresholds

`payday-spike.js` fails the run if p95 payment latency exceeds 300ms or the
success rate falls below 99 percent. The point of the scenario is not that
the platform survives peak load, but that customer visible latency holds
while it scales.

`rollback-drill.js` sets no thresholds. It is expected to fail during the
bad deploy; the measurement is how long the failure lasts.

## Drill timing

Both drill scenarios print their timeline at startup, including the exact
commands to run at each point.
