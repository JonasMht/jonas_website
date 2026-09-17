#!/usr/bin/env bash
# Station deploy — build + rsync to the home server. Manual by design.
set -euo pipefail

USER_HOST="${DEPLOY_TARGET:-jonas@10.0.0.12}"
SITE_DIR="/srv/jonasx/site"
TEL_DIR="/srv/jonasx/telemetry"

cd "$(dirname "$0")/.."

echo "[1/3] building…"
/tmp/opencode/hugo --gc --minify

echo "[2/3] syncing site → ${USER_HOST}:${SITE_DIR}"
rsync -az --delete public/ "${USER_HOST}:${SITE_DIR}/"

echo "[3/3] syncing telemetry pack → ${USER_HOST}:${TEL_DIR}"
rsync -az --delete telemetry/server.py telemetry/dashboard.html "${USER_HOST}:${TEL_DIR}/"

echo "done. dashboard: https://jonasx.xyz/dash?key=<your TELEMETRY_KEY>"
echo "if the collector changed: ssh ${USER_HOST} 'systemctl --user restart jonasx-telemetry'"
echo "if the Caddyfile changed:  ssh ${USER_HOST} 'systemctl --user reload jonasx-caddy'"
