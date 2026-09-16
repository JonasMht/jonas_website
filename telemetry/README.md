# Station Telemetry — deployment pack

Self-hosted, first-party analytics: collector + SQLite + owner dashboard.
Stdlib-only Python — no pip, no services, one process.

## Layout on the VPS (`10.0.0.12`)

```
/srv/jonasx/
  site/        ← rsynced ./public (static site, Caddy serves it)
  telemetry/
    server.py       this collector
    dashboard.html  owner dashboard
    telemetry.db    sqlite (auto-created)
```

## 1. Provision (Debian)

```bash
sudo apt install -y caddy sqlite3
sudo useradd -r -s /usr/sbin/nologin telemetry
sudo mkdir -p /srv/jonasx/telemetry && sudo chown telemetry:telemetry /srv/jonasx/telemetry
sudo cp telemetry/server.py telemetry/dashboard.html /srv/jonasx/telemetry/
```

## 2. systemd service (sandboxed)

`/etc/systemd/system/station-telemetry.service`:

```ini
[Unit]
Description=Station Telemetry collector
After=network.target

[Service]
User=telemetry
Group=telemetry
ExecStart=/usr/bin/python3 /srv/jonasx/telemetry/server.py
Environment=TELEMETRY_DB=/srv/jonasx/telemetry/telemetry.db
Environment=TELEMETRY_ORIGIN=https://jonasx.xyz
Environment=TELEMETRY_KEY=__GENERATE_AND_PASTE__
Restart=always
RestartSec=3
# sandbox
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/srv/jonasx/telemetry
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
SystemCallArchitectures=native

[Install]
WantedBy=multi-user.target
```

Generate the key once: `python3 -c "import secrets;print(secrets.token_urlsafe(24))"`
→ put it in the unit, and use it on the dashboard URL.

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now station-telemetry
```

## 3. Caddyfile (site + telemetry, same origin)

```
jonasx.xyz {
    root * /srv/jonasx/site
    encode gzip
    try_files {path} {path}/ /index.html
    file_server
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
        Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    }
    reverse_proxy /e   127.0.0.1:8765
    reverse_proxy /dash* 127.0.0.1:8765
    reverse_proxy /api* 127.0.0.1:8765
    # gentle edge rate-limit for the intake endpoint
    rate_limit {
        zone intake { key {remote_host} events 240 window 1m }
    }
}
```

(The `rate_limit` directive needs Caddy ≥ 2.8 with the rate_limit plugin, or
skip it — the collector has its own in-process limiter.)

## 4. Home-server exposure (10.0.0.12 is a LAN address)

The box is on your LAN — to serve the public internet, pick ONE:

- **Router port-forward** 80/443 → 10.0.0.12 + dynamic DNS (your router or
  ddclient). Simple, fully yours, exposes your home IP.
- **Cloudflare Tunnel** (`cloudflared`) — no open ports, hides home IP,
  free TLS; trade-off: traffic transits Cloudflare (still your data, their pipe).

## 5. Deploy the site (manual, per your choice)

`scripts/deploy.sh` — builds with Hugo, rsyncs `public/` + `telemetry/` to the
box, prints the dashboard URL. Adjust USER/HOST at the top if needed.

## 6. Flip the beacon

In `config/_default/params.toml` set:

```toml
telemetryEndpoint = "https://jonasx.xyz/e"
```

Same origin as the site → no CORS complexity, CSP `connect-src 'self'` holds.
Rebuild + deploy. The dashboard: `https://jonasx.xyz/dash?key=YOUR_KEY`.

## Verify

```bash
curl -s -X POST https://jonasx.xyz/e -H 'Content-Type: application/json' \
  -d '{"t":"pv","p":"/","v":"test-visitor","s":"test-session"}' -o /dev/null -w '%{http_code}\n'
# expect 204 — then open the dashboard and see the event land.
```
