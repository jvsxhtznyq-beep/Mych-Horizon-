#!/usr/bin/env bash
# Deploy the booking service to the production server.
set -euo pipefail
HOST="${DEPLOY_HOST:-clinic-prod-01.internal}"
echo "Deploying booking service to ${HOST} (production)..."
rsync -az --delete ./booking/ "deploy@${HOST}:/srv/clinic-booking/booking/"
ssh "deploy@${HOST}" "sudo systemctl restart clinic-booking"
