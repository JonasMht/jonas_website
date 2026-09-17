# Go-live checklist (redesign → public)

Ordered list for publishing the redesign on the real domain. Execute in order,
tick as you go. All box commands assume `ssh jonas@10.0.0.12`.

## 1. Pre-flight (already done, re-verify)
- [ ] Collector + Caddy run as systemd user services and survive reboot:
      `systemctl --user is-active jonasx-telemetry jonasx-caddy`
- [ ] Nightly DB backup cron installed (`crontab -l`)
- [ ] `telemetry/blocked.txt` and bans sane (`tail telemetry/server.log`)

## 2. Domain + TLS
- [ ] DNS: point `jonasx.xyz` (A/AAAA) at the home IP or tunnel
- [ ] Router: forward 443/80 → 10.0.0.12, or run `cloudflared` tunnel
- [ ] Production Caddyfile: copy the working `:8090` block to a `jonasx.xyz`
      block — Caddy then issues certificates automatically (HTTP-01)
- [ ] Keep the system Caddy (`/etc/caddy/Caddyfile`) untouched; add the block
      there OR run a second user instance on :443 — one of the two, never both
- [ ] `curl -I https://jonasx.xyz/` → 200, certificate valid, headers intact

## 3. Beacon flip
- [ ] `config/_default/params.toml`: `telemetryEndpoint = "https://jonasx.xyz/e"`
- [ ] Build + deploy: `./scripts/deploy.sh`
- [ ] Visit the site from another device → `/dash?key=…` shows the pageview
- [ ] Origin check: the collector `ORIGIN` must match the public URL
      (edit `telemetry/server.py` `ORIGIN` default or pass env) — mismatch = 403s

## 4. Keys
- [ ] Rotate the telemetry key for production: delete `telemetry/.key` on the
      box, `systemctl --user restart jonasx-telemetry`, note the new key
- [ ] Dashboard URL is private: don't publish it anywhere

## 5. Content truth
- [ ] `content/legal/index.md`: hosting line still says GitHub Pages — update
      to the real host (home server / tunnel) before merge
- [ ] robots.txt + sitemap.xml reachable on the public URL
- [ ] Search-console style smoke: every top nav route returns 200, one 404 spot-check

## 6. Merge order
- [ ] Final review of `redesign/pro-personal` diff vs `master`
- [ ] Merge (fast-forward or PR), push `master`
- [ ] `deploy.yml` fires on master pushes — keep it (build check) even if the
      box is the origin; or retire it if GitHub Pages is no longer the host
- [ ] Post-merge: hard-refresh once, run the beacon check again

## 7. After go-live
- [ ] Watch `server.log` for 429/403 spam the first week
- [ ] Weekly glance at the dashboard; monthly DB backup restore drill
