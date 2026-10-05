#!/usr/bin/env bash
# Deploy all services to EKS.
#
# Database hosts are overridden here rather than in the values files. The
# values describe the local topology, where one Postgres serves every
# service. On AWS each service has its own RDS instance, and the endpoints
# are read from Terraform rather than copied by hand.
#
# Usage: ./scripts/deploy-eks.sh 3.0.0

set -euo pipefail

TAG="${1:?usage: deploy-eks.sh <image-tag>}"
REGION="eu-west-2"
TFDIR="infrastructure/terraform/environments/dev"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ECR="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"

RDS_SUFFIX=$(terraform -chdir="$TFDIR" output -json database_endpoints \
  | python -c 'import json,sys; print(list(json.load(sys.stdin).values())[0].split(".",1)[1])')
REDIS=$(terraform -chdir="$TFDIR" output -raw redis_endpoint)

echo "RDS suffix: $RDS_SUFFIX"
echo "Redis:      $REDIS"
echo

deploy() {
  local svc="$1" db="${2:-}"
  echo "--- $svc"
  if [ -n "$db" ]; then
    helm upgrade --install "$svc" kubernetes/helm/meridian-service \
      -f "kubernetes/helm/values/${svc}.yaml" \
      --set image.repository="${ECR}/meridian-pay/${svc}" \
      --set image.tag="$TAG" \
      --set env.REDIS_HOST="$REDIS" \
      --set env.DB_HOST="meridian-pay-dev-${db}.${RDS_SUFFIX}" \
      --set env.DB_NAME="$db"
  else
    helm upgrade --install "$svc" kubernetes/helm/meridian-service \
      -f "kubernetes/helm/values/${svc}.yaml" \
      --set image.repository="${ECR}/meridian-pay/${svc}" \
      --set image.tag="$TAG" \
      --set env.REDIS_HOST="$REDIS"
  fi
}

deploy api-gateway
deploy auth-service auth
deploy account-service account
deploy payment-service payment
deploy ledger-service ledger
deploy fraud-service fraud
deploy fx-service fx
deploy notification-service notification

echo
echo "Deployed tag ${TAG}"
