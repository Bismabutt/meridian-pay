#!/bin/bash
# Deploy script. Run from your laptop, connected to the VPN.
# Ask Amir before running this against prod.

SERVER=${1:-prod-app-01}
SERVICE=${2}

if [ -z "$SERVICE" ]; then
  echo "Usage: ./deploy.sh <server> <service>"
  exit 1
fi

echo "Deploying $SERVICE to $SERVER..."

ssh deploy@$SERVER << EOF
  cd /opt/meridian/$SERVICE
  git pull origin main
  pip install -r requirements.txt
  sudo systemctl restart meridian-$SERVICE
  sleep 3
  curl -f http://localhost:800*/health || echo "WARNING: health check failed"
EOF

echo "Done. Check the logs if anything looks wrong."
