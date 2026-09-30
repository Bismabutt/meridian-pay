# ADR-005: Spot capacity for development worker nodes

**Status:** Accepted
**Date:** 2026-09

## Context

Worker node compute is the second largest cost after the EKS control plane.
Spot capacity is priced at roughly 30 percent of on demand but can be
reclaimed with two minutes notice.

## Decision

Spot capacity for the development node group.

## Alternatives considered

**On demand throughout.** Predictable, no reclamation. Rejected on cost.

**A mixed node group**, on demand for critical workloads and spot for the
rest. Deferred as unnecessary complexity for a development environment.

## Consequences

Roughly 70 percent saving on node cost. Kubernetes reschedules pods
automatically on reclamation, which is acceptable for stateless development
workloads.

Production would run on demand for money zone services, where an interrupted
payment is not acceptable, and spot only for tolerant workloads such as
fraud scoring consumers.
