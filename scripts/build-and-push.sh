#!/usr/bin/env bash
#
# Build and push all service images to ECR.
#
# Built for linux/amd64 explicitly with attestations disabled. Docker
# Desktop's default buildx output is a multi platform manifest list, which
# containerd on EKS cannot unpack: pods fail with "mismatched image rootfs
# and manifest layers" or "no command specified".
#
# Usage: ./scripts/build-and-push.sh 3.0.0

set -euo pipefail

TAG="${1:?usage: build-and-push.sh <tag>}"
REGION="eu-west-2"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ECR="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"

SERVICES="api-gateway auth-service account-service payment-service ledger-service fraud-service fx-service notification-service"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR"

for s in $SERVICES; do
  echo "--- $s"
  docker buildx build \
    --platform linux/amd64 \
    --provenance=false \
    --sbom=false \
    -t "${ECR}/meridian-pay/${s}:${TAG}" \
    --push \
    "./services/${s}"
done

echo "--- payment-service:broken"
docker buildx build \
  --platform linux/amd64 --provenance=false --sbom=false \
  -t "${ECR}/meridian-pay/payment-service:broken-${TAG}" \
  --push /tmp/broken-payment

echo
echo "Pushed tag ${TAG}. Deploy with --set image.tag=${TAG}"
