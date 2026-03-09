#!/bin/bash
# Pull latest code and restart the service
set -euo pipefail

APP_DIR="/opt/leadgen"

echo "Pulling latest code..."
git -C "$APP_DIR" pull --ff-only

echo "Installing any new dependencies..."
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt" -q

echo "Restarting API service..."
systemctl restart leadgen

sleep 2
systemctl is-active --quiet leadgen && echo "✅ leadgen service is running" || echo "❌ leadgen service failed"
echo "Done."
