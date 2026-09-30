# ADR-006: for_each rather than count for per service resources

**Status:** Accepted
**Date:** 2026-09

## Context

Seven databases and eight container registries are created from single
Terraform resource blocks. Terraform offers `count`, which keys resources by
list index, and `for_each`, which keys by map key.

## Decision

`for_each` for all per service resources. `count` retained only for
interchangeable resources such as subnets.

## Alternatives considered

**`count` throughout.** Simpler to write and read.

Rejected because resources keyed by index shift when an item is removed from
the list. Removing the fifth of seven databases would cause Terraform to see
the sixth as now being the fifth, and destroy and recreate databases that had
not changed.

## Consequences

Removing one service from the map destroys only that service's resources.
Databases named in state as `aws_db_instance.main["ledger"]` rather than
`aws_db_instance.main[3]` are also considerably easier to read in a plan.

The configuration is slightly more verbose.
