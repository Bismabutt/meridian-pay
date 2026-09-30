# ADR-007: Generated credentials in Secrets Manager

**Status:** Accepted
**Date:** 2026-09

## Context

Discovery established that database passwords were held in a shared
spreadsheet and hardcoded in service configuration, accessible to people who
had left the company.

## Decision

Terraform generates a 32 character password per database and writes it to AWS
Secrets Manager. No human sees or types it. Applications retrieve credentials
at runtime through IAM Roles for Service Accounts.

## Alternatives considered

**HashiCorp Vault.** The programme charter names Vault, and it offers dynamic
short lived credentials which are stronger than static ones.

Rejected for this project because Secrets Manager combined with IRSA achieves
the outcome that matters: no credential is stored in the cluster, in the
repository, or anywhere a person can read it. Running Vault would add an
operational component, including unsealing, for a benefit this platform does
not currently need.

**RDS managed master passwords**, which remove the value from Terraform state
entirely. Deferred, as it complicates the local development path.

## Consequences

Credentials are unique per database, rotatable without application changes,
and absent from version control.

The generated value does appear in Terraform state, which is why state is
encrypted in S3 with versioning and excluded from git.

Automatic rotation is not configured. That requires a Lambda rotation
function and is a genuine gap, recorded here rather than left unstated.
