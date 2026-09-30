# ADR-004: One NAT gateway in non production

**Status:** Accepted
**Date:** 2026-09

## Context

Private subnets require outbound internet access to pull container images and
reach external partners. A NAT gateway costs approximately 32 USD per month
plus data processing charges. Standard practice is one per availability zone.

## Decision

One NAT gateway in the development environment, shared by all three private
subnets. Controlled by a boolean variable.

## Alternatives considered

**One NAT gateway per availability zone**, the production pattern. Rejected
on cost for a non production environment on a constrained budget.

## Consequences

An availability zone failure would remove outbound connectivity for all
private subnets rather than only the affected zone.

Acceptable in development. Production sets `single_nat_gateway = false` and
provisions one per zone, at roughly 96 USD per month rather than 32.

This should be revisited before this configuration is used as the basis for
any environment carrying real traffic.
