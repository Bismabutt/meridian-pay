# ADR-002: Kafka self managed via Strimzi rather than Amazon MSK

**Status:** Accepted
**Date:** 2026-08

## Context

Payment events are carried on Kafka: `payment.initiated`, `payment.cleared`,
`payment.failed`. fraud-service and notification-service consume them
asynchronously. Amazon MSK and self managed Kafka via the Strimzi operator
both provide this.

## Decision

Kafka self managed in the cluster, using the Strimzi operator.

## Alternatives considered

**Amazon MSK.** Managed brokers, automated patching, no operator to run.
Rejected primarily on cost for a non production environment: the smallest MSK
cluster costs substantially more per month than brokers running on existing
cluster capacity.

## Consequences

The entire platform, including the event bus, is reproducible from git.
Topics are declared as Kubernetes resources with explicit partition counts
and retention, so those are deliberate rather than whatever the first
producer happened to create.

Broker lifecycle, upgrades and failure handling become our responsibility.
The Strimzi operator handles most of this, but it is one more component to
understand.

For a production deployment of this scale, MSK would be the stronger choice.
The decision here is driven by a non production cost constraint, and that
should be revisited before any environment carries real traffic.
