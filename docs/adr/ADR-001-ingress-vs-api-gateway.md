# ADR-001: NGINX Ingress Controller rather than AWS API Gateway

**Status:** Accepted
**Date:** 2026-08

## Context

Customer traffic needs a single entry point that terminates TLS, applies rate
limits, validates authentication and routes to services. AWS API Gateway and
an in cluster ingress controller both do this.

## Decision

NGINX Ingress Controller running in the cluster, behind an AWS Application
Load Balancer.

## Alternatives considered

**AWS API Gateway.** Managed, no capacity to plan, native integration with
AWS authentication. Rejected because request pricing becomes significant at
500 payments per second sustained plus 3,000 balance reads, and because
routing configuration would live outside the cluster, splitting deployment
across two systems.

## Consequences

Routing rules are Kubernetes resources, so they deploy with everything else
and are reconciled by ArgoCD. The ingress controller is capacity we manage
and must scale.

The ALB still terminates TLS and provides WAF, so AWS handles the parts where
managed services are unambiguously better.
