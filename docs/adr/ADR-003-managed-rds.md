# ADR-003: Managed RDS rather than PostgreSQL in the cluster

**Status:** Accepted
**Date:** 2026-08

## Context

Seven services each require their own PostgreSQL database. These could run as
StatefulSets in the cluster or as managed RDS instances.

## Decision

Amazon RDS, one instance per service.

## Alternatives considered

**PostgreSQL in cluster via an operator.** Cheaper, and keeps everything in
one place. Rejected because the ledger is the authoritative record of
customer funds, and backup, point in time recovery and failover are not areas
to economise on.

## Consequences

Automated backups, point in time recovery, and multi AZ failover for the
money zone databases come without us building them.

Databases are sized independently per service, which matters: the ledger and
payment databases get multi AZ and seven day retention, while notification
gets the smallest instance and one day.

Cost is higher than in cluster PostgreSQL, and the databases live outside
the Kubernetes reconciliation loop. Terraform owns them instead.
