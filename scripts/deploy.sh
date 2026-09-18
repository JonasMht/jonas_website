#!/usr/bin/env bash
# Station deploy — build + rsync to the home server. Manual by design.
set -euo pipefail

USER_HOST="${DEPLOY_TARGET:-jonas@10.0.0.12}"
SITE_DIR="/srv/jonasx/site"
TEL_DIR="/srv/jonasx/telemetry"

cd "$(dirname "$0")/.."

echo "[1/3] building…"
HUGO="${HUGO:-$(command -v hugo || echo /tmp/opencode/hugo)}"
"$HUGO" --gc --minify

echo "[2/3] syncing site → ${USER_HOST}:${SITE_DIR}"
rsync -az --delete public/ "${USER_HOST}:${SITE_DIR}/"

echo "[3/3] syncing telemetry pack → ${USER_HOST}:${TEL_DIR}"
CHANGED=$(rsync -az --delete --itemize-changes telemetry/server.py telemetry/dashboard.html "${USER_HOST}:${TEL_DIR}/" | grep -c "^>f" || true)

echo "done. dashboard: https://jonasx.xyz/dash?key=<your TELEMETRY_KEY>"
if [ "${CHANGED:-0}" -gt 0 ]; then
    echo "collector files changed — restarting service…"
    ssh "${USER_HOST}" "systemctl --user restart jonasx-telemetry"
    sleep 2
    ssh "${USER_HOST}" "curl -fsS http://127.0.0.1:8819/api/pulse > /dev/null" && echo "collector healthy" || echo "WARNING: collector did not come up"
fi
echo "if the Caddyfile changed:  ssh ${USER_HOST} 'systemctl --user reload jonasx-caddy'"
