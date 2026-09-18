#!/usr/bin/env python3
"""
JONASX STATION TELEMETRY — self-hosted event collector + dashboard.

Stdlib only (no pip). Designed to run sandboxed behind Caddy:
    caddy:  reverse_proxy /e*  /dash*  /api*  ->  127.0.0.1:8765

Endpoints
  POST /e                event intake (public, CORS-restricted, rate-limited)
  GET  /dash?key=KEY     owner dashboard
  GET  /api/summary?key=KEY           totals, top pages, referrers, devices
  GET  /api/heatmap?key=KEY&page=P    click coordinates for one page
  GET  /api/visitors?key=KEY&limit=N  pseudonymous visitor profiles
  GET  /api/visitor?key=KEY&id=ID     one profile's full timeline

Env
  TELEMETRY_KEY   dashboard/API key (default: random, printed at start)
  TELEMETRY_DB    sqlite path             (default: ./telemetry.db)
  TELEMETRY_PORT  listen port             (default: 8765)
  TELEMETRY_ORIGIN allowed CORS origin    (default: https://jonasx.xyz)

Retention: events 90 days, visitor rows 400 days (pruned hourly).
"""
import json, os, pathlib, random, sqlite3, string, time, threading, hashlib, hmac, socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

KEY = os.environ.get("TELEMETRY_KEY") or "".join(random.choices(string.ascii_letters + string.digits, k=32))
DB = os.environ.get("TELEMETRY_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "telemetry.db"))
PORT = int(os.environ.get("TELEMETRY_PORT", "8765"))
ORIGIN = os.environ.get("TELEMETRY_ORIGIN", "https://jonasx.xyz")
HERE = os.path.dirname(os.path.abspath(__file__))
EVENT_TTL = 90 * 86400
VISITOR_TTL = 400 * 86400
RATE = {}  # ip -> [window_start, count]
RATE_MAX, RATE_WIN = 120, 60          # requests per IP per minute
BAN_SECS = 900                         # 15-minute escalating temp ban
BANS = {}                              # ip -> [banned_until, strikes]
STARTED = int(time.time())             # collector boot time, exposed via /api/pulse
BLOCKFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blocked.txt")
BLOCKED = set()
BLOCKED_MTIME = 0
MAX_CONNS = 32
CONN_SEM = threading.BoundedSemaphore(MAX_CONNS)

def _load_blockfile():
    global BLOCKED, BLOCKED_MTIME
    try:
        m = os.path.getmtime(BLOCKFILE)
        if m != BLOCKED_MTIME:
            with open(BLOCKFILE) as f:
                BLOCKED = {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}
            BLOCKED_MTIME = m
    except FileNotFoundError:
        BLOCKED = set(); BLOCKED_MTIME = 0

def _prune_rates(now):
    if len(RATE) > 4096:
        for ip in [ip for ip, (w, _) in RATE.items() if now - w > RATE_WIN]:
            RATE.pop(ip, None)
    for ip in [ip for ip, (until, _) in BANS.items() if until < now]:
        BANS.pop(ip, None)

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL, v TEXT, s TEXT, t TEXT NOT NULL, p TEXT,
    x REAL, y REAL, d INTEGER, w INTEGER, r TEXT, b TEXT, ip TEXT, c TEXT
);
CREATE INDEX IF NOT EXISTS ev_ts ON events(ts);
CREATE INDEX IF NOT EXISTS ev_p ON events(p);
CREATE INDEX IF NOT EXISTS ev_t_ts ON events(t, ts);
CREATE INDEX IF NOT EXISTS ev_v ON events(v);
CREATE TABLE IF NOT EXISTS visitors (
    v TEXT PRIMARY KEY, first INTEGER NOT NULL, last INTEGER NOT NULL,
    visits INTEGER NOT NULL DEFAULT 1
);
"""

def db():
    c = sqlite3.connect(DB, timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    return c

def prune_loop():
    while True:
        try:
            with db() as c:
                now = int(time.time())
                c.execute("DELETE FROM events WHERE ts < ?", (now - EVENT_TTL,))
                c.execute("DELETE FROM visitors WHERE last < ?", (now - VISITOR_TTL,))
        except Exception:
            pass
        time.sleep(3600)

def rate_ok(ip, cost=1):
    """Per-IP event-budget throttle with escalating temp bans + permanent blocklist."""
    global BLOCKED_MTIME
    now = time.time()
    _prune_rates(now)
    _load_blockfile()
    if ip in BLOCKED:
        print("[station-telemetry] BLOCKED hit from %s" % ip, flush=True)
        return False, -403
    until, strikes = BANS.get(ip, (0, 0))
    if until > now:
        return False, int(until - now)
    win, n = RATE.get(ip, (0, 0))
    if now - win > RATE_WIN:
        RATE[ip] = (now, cost); return True, 0
    if n + cost > RATE_MAX:
        strikes += 1
        BANS[ip] = (now + BAN_SECS * strikes, strikes)   # linear escalation: +15 min per repeat
        RATE.pop(ip, None)
        print("[station-telemetry] BAN %s for %ds (strike %d)" % (ip, BAN_SECS * strikes, strikes), flush=True)
        return False, BAN_SECS * strikes
    RATE[ip] = (win, n + cost); return True, 0

def touch_visitor(cur, v, ts):
    cur.execute("INSERT INTO visitors(v, first, last) VALUES(?,?,?) ON CONFLICT(v) DO UPDATE SET last=excluded.last, visits=visits+1", (v, ts, ts))

class Handler(BaseHTTPRequestHandler):
    server_version = "StationTelemetry/1.0"
    timeout = 15                              # kill slow/idle connections
    protocol_version = "HTTP/1.1"
    def log_message(self, fmt, *a): pass
    def handle_one_request(self):
        try:
            BaseHTTPRequestHandler.handle_one_request(self)
        except (socket.timeout, ConnectionError):
            self.close_connection = True

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Vary", "Origin")

    def _json(self, code, obj, cors=False):
        self.send_response(code)
        if code == 204 or obj is None:
            if cors: self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = json.dumps(obj).encode()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if cors: self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_POST(self):
        xff = (self.headers.get("X-Forwarded-For") or "").split(",")
        ip = xff[-1].strip() if xff and xff[-1].strip() else self.client_address[0]
        origin = self.headers.get("Origin", "")
        if origin and origin != ORIGIN:
            self.close_connection = True
            return self._json(403, {"e": "bad origin"}, cors=True)
        if urlparse(self.path).path != "/e":
            return self._json(404, {"e": "not found"})
        try:
            n = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            n = 0
        if n > 16384:
            self.rfile.read(16384)                     # drain a bounded slice
            self.send_response(413)
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self._cors(); self.end_headers()
            self.close_connection = True
            return
        body = self.rfile.read(n) if n > 0 else b""

        try:
            data = json.loads(body) if body else []
        except Exception:
            return self._json(400, {"e": "bad json"}, cors=True)
        if not isinstance(data, list): data = [data]
        # charge the event budget, not the request count — a batch of N costs N
        ok, retry = rate_ok(ip, max(1, min(len(data), 40)))
        if not ok:
            self.close_connection = True
            if retry == -403:
                return self._json(403, {"e": "blocked"}, cors=True)
            self.send_response(429)
            self.send_header("Retry-After", str(retry))
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self._cors(); self.end_headers()
            return
        try:
            data = json.loads(body) if body else []
        except Exception:
            return self._json(400, {"e": "bad json"}, cors=True)
        if not isinstance(data, list): data = [data]
        now = int(time.time())
        iph = hashlib.sha256(("jm:" + ip).encode()).hexdigest()[:16]
        rows = []
        for ev in data[:40]:
            if not isinstance(ev, dict): continue
            t = str(ev.get("t", ""))[:8]
            if t not in ("pv", "clk", "dur"): continue
            try:
                rows.append((now, str(ev.get("v", ""))[:40], str(ev.get("s", ""))[:40], t,
                             str(ev.get("p", "/"))[:200].replace("<", "").replace(">", ""),
                             max(0.0, min(1.0, float(ev.get("x", 0) or 0))),
                             max(0.0, min(1.0, float(ev.get("y", 0) or 0))),
                             max(0, min(100, int(ev.get("d", 0) or 0))),
                             max(0, min(36000, int(ev.get("w", 0) or 0))),
                             str(ev.get("r", ""))[:120].replace("<", "").replace(">", ""),
                             str(ev.get("b", ""))[:160].replace("<", "").replace(">", ""), iph,
                             self.headers.get("CF-IPCountry", "")[:8]))
            except (TypeError, ValueError):
                continue
        try:
            with db() as c:
                cur = c.cursor()
                for v in {r[1] for r in rows if r[1]}:
                    touch_visitor(cur, v, now)
                cur.executemany(
                    "INSERT INTO events(ts,v,s,t,p,x,y,d,w,r,b,ip,c) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        except Exception:
            return self._json(500, {"e": "db"}, cors=True)
        self._json(204, {}, cors=True)

    def _auth(self, q):
        return hmac.compare_digest(q.get("key", [""])[0], KEY)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/dash" and self._auth(q):
            try:
                with open(os.path.join(HERE, "dashboard.html"), "rb") as f:
                    body = f.read().replace(b"__KEY__", KEY.encode())
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Robots-Tag", "noindex, nofollow")
                self.end_headers(); self.wfile.write(body)
            except Exception:
                self._json(500, {"e": "dashboard missing"})
            return
        if u.path == "/api/pulse":
            self._json(200, api_pulse(), cors=True)
            return
        if u.path.startswith("/api/"):
            if not self._auth(q):
                return self._json(403, {"e": "bad key"})
            name = u.path[5:]
            fn = {"summary": api_summary, "heatmap": api_heatmap,
                  "visitors": api_visitors, "visitor": api_visitor}.get(name)
            if not fn: return self._json(404, {"e": "unknown endpoint"})
            self._json(200, fn(q), cors=True)
            return
        self._json(404, {"e": "not found"})

def _q_days(q, default=30):
    try: return max(1, min(365, int(q.get("days", [default])[0])))
    except Exception: return default

_PULSE = {"at": 0, "data": None}       # cached public aggregates (30s)
def api_pulse():
    """Public, keyless aggregates — nothing personal, safe to publish. Cached 30s."""
    now = int(time.time())
    if _PULSE["data"] and now - _PULSE["at"] < 30:
        d = dict(_PULSE["data"]); d["now"] = now; return d
    week = now - 7 * 86400
    with db() as c:
        cur = c.cursor()
        def one(sql, *a):
            cur.execute(sql, a); r = cur.fetchone(); return r[0] if r else 0
        v7 = one("SELECT COUNT(DISTINCT v) FROM events WHERE ts >= ?", week)
        pv_total = one("SELECT COUNT(*) FROM events WHERE t = 'pv'")
        pages = one("SELECT COUNT(DISTINCT p) FROM events WHERE t = 'pv'")
    d = {"v7": v7, "pv_total": pv_total, "pages": pages, "since": STARTED, "now": now}
    _PULSE["at"] = now; _PULSE["data"] = d
    return d

def api_summary(q):
    days = _q_days(q)
    since = int(time.time()) - days * 86400
    day_ago = int(time.time()) - 86400
    with db() as c:
        cur = c.cursor()
        def one(sql, *a):
            cur.execute(sql, a); r = cur.fetchone(); return r[0] if r else 0
        def many(sql, *a):
            cur.execute(sql, a); return [list(r) for r in cur.fetchall()]
        return {
            "days": days,
            "views_total": one("SELECT COUNT(*) FROM events WHERE t='pv' AND ts>?", since),
            "views_today": one("SELECT COUNT(*) FROM events WHERE t='pv' AND ts>?", day_ago),
            "uniques_total": one("SELECT COUNT(DISTINCT v) FROM events WHERE t='pv' AND ts>?", since),
            "uniques_today": one("SELECT COUNT(DISTINCT v) FROM events WHERE t='pv' AND ts>?", day_ago),
            "sessions": one("SELECT COUNT(DISTINCT s) FROM events WHERE ts>?", since),
            "clicks": one("SELECT COUNT(*) FROM events WHERE t='clk' AND ts>?", since),
            "returns": one("SELECT COUNT(*) FROM visitors WHERE visits>1 AND last>?", since),
            "pages": many("SELECT p, COUNT(*) n FROM events WHERE t='pv' AND ts>? GROUP BY p ORDER BY n DESC LIMIT 12", since),
            "refs": many("SELECT COALESCE(NULLIF(r,''),'(direct)'), COUNT(*) n FROM events WHERE t='pv' AND ts>? GROUP BY 1 ORDER BY n DESC LIMIT 10", since),
            "devices": many("SELECT CASE WHEN b LIKE '%mobile%' OR b LIKE '%Android%' OR b LIKE '%iPhone%' THEN 'mobile' WHEN b LIKE '%iPad%' OR b LIKE '%tablet%' THEN 'tablet' ELSE 'desktop' END k, COUNT(*) n FROM events WHERE t='pv' AND ts>? GROUP BY k", since),
            "hours": many("SELECT (ts/3600)*3600 h, COUNT(*) n FROM events WHERE t='pv' AND ts>? GROUP BY h ORDER BY h", day_ago),
        }

def api_heatmap(q):
    days = _q_days(q, 30)
    page = q.get("page", ["/"])[0]
    since = int(time.time()) - days * 86400
    with db() as c:
        cur = c.cursor()
        cur.execute("SELECT x, y FROM events WHERE t='clk' AND p=? AND ts>?", (page, since))
        clicks = cur.fetchall()
        cur.execute("SELECT AVG(d) FROM events WHERE t='dur' AND p=? AND ts>?", (page, since))
        avg_depth = (cur.fetchone() or [0])[0]
        cur.execute("SELECT COUNT(*) FROM events WHERE t='pv' AND p=? AND ts>?", (page, since))
        views = cur.fetchone()[0]
    return {"page": page, "days": days, "views": views, "avg_depth": round(avg_depth or 0, 1), "clicks": clicks}

def api_visitors(q):
    days = _q_days(q, 30)
    try: limit = max(1, min(200, int(q.get("limit", [50])[0])))
    except Exception: limit = 50
    since = int(time.time()) - days * 86400
    with db() as c:
        cur = c.cursor()
        cur.execute("SELECT v, first, last, visits FROM visitors WHERE last>? ORDER BY last DESC LIMIT ?", (since, limit))
        out = []
        for v, first, last, visits in cur.fetchall():
            short = v[:8] if v else "?"
            cur.execute("SELECT p, COUNT(*) FROM events WHERE v=? AND t='pv' AND ts>? GROUP BY p ORDER BY 2 DESC LIMIT 5", (v, since))
            pages = cur.fetchall()
            cur.execute("SELECT COUNT(DISTINCT s) FROM events WHERE v=? AND ts>?", (v, since))
            sess = cur.fetchone()[0]
            out.append({"id": short, "first": first, "last": last, "visits": visits,
                        "sessions": sess, "pages": pages})
    return {"days": days, "visitors": out}

def api_visitor(q):
    vid = q.get("id", [""])[0]
    since = int(time.time()) - _q_days(q) * 86400
    with db() as c:
        cur = c.cursor()
        cur.execute("SELECT rowid FROM visitors WHERE v LIKE ?", (vid + "%",))
        row = cur.fetchone()
        if not row: return {"e": "unknown"}
        cur.execute("SELECT v FROM visitors WHERE rowid=?", (row[0],))
        full = cur.fetchone()[0]
        cur.execute("SELECT ts, t, p, w, d FROM events WHERE v=? AND ts>? ORDER BY ts LIMIT 500", (full, since))
        evs = cur.fetchall()
    return {"id": vid, "events": evs}

class LimitedServer(ThreadingHTTPServer):
    daemon_threads = True
    def process_request(self, request, client_address):
        if not CONN_SEM.acquire(blocking=False):        # shed load when saturated
            try:
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nRetry-After: 5\r\nConnection: close\r\n\r\n")
            except Exception:
                pass
            self.shutdown_request(request)
            return
        threading.Thread(target=self._guarded, args=(request, client_address), daemon=True).start()
    def _guarded(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            pass
        finally:
            self.shutdown_request(request)
            CONN_SEM.release()

def run():
    with db() as c: c.executescript(SCHEMA)
    pathlib.Path(BLOCKFILE).touch(exist_ok=True)
    threading.Thread(target=prune_loop, daemon=True).start()
    print(f"[station-telemetry] dashboard key: {KEY}")
    print(f"[station-telemetry] rate: {RATE_MAX}/{RATE_WIN}s per IP, escalating bans per IP for {BAN_SECS}s, blocklist={BLOCKFILE}")
    print(f"[station-telemetry] listening on 127.0.0.1:{PORT}, db={DB}, origin={ORIGIN}")
    LimitedServer(("127.0.0.1", PORT), Handler).serve_forever()

if __name__ == "__main__":
    run()
