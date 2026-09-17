#!/usr/bin/env python3
"""Record interaction showcases of the station — mp4 via playwright + ffmpeg."""
import subprocess, time, pathlib
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8818/"
OUT = pathlib.Path("design-lab/previews/videos")
OUT.mkdir(parents=True, exist_ok=True)
RAW = OUT / "raw"
RAW.mkdir(exist_ok=True)

def record(name, fn, seconds_pad=1.0, viewport=None):
    vp = viewport or {"width": 1440, "height": 900}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport=vp,
            record_video_dir=str(RAW),
            record_video_size=vp,
        )
        page = ctx.new_page()
        try:
            fn(page)
        finally:
            time.sleep(seconds_pad)
            v = page.video
            ctx.close()
            browser.close()
        # find newest video file
        vids = sorted(RAW.glob("*.webm"), key=lambda f: f.stat().st_mtime)
        src = vids[-1]
        dst = OUT / (name + ".mp4")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(dst),
        ], check=True)
        src.unlink()
        print("recorded", dst, dst.stat().st_size // 1024, "KB")

def scroll_pass(page, step=500, ms=180):
    h = page.evaluate("document.body.scrollHeight")
    y = 0
    while y <= h:
        page.evaluate(f"window.scrollTo({{top:{y},behavior:'instant'}})")
        page.wait_for_timeout(ms)
        y += step

def v1(page):  # arrival: ignition → power-on → hover reticles
    page.goto(BASE)
    page.wait_for_timeout(900)
    scroll_pass(page, 350, 260)
    page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
    page.wait_for_timeout(500)
    cards = page.locator(".grid3 .card")
    for i in range(cards.count()):
        cards.nth(i).hover()
        page.wait_for_timeout(650)
    page.locator(".spotlight").hover()
    page.wait_for_timeout(700)
    page.locator(".lnk.pri").hover()
    page.wait_for_timeout(500)

def v2(page):  # console: open → help → session → telemetry off/on → close
    page.goto(BASE)
    page.wait_for_timeout(900)
    page.keyboard.press("`")
    page.wait_for_timeout(500)
    for cmd in ["help", "session", "telemetry off", "telemetry on", "goto /pro/"]:
        page.keyboard.type(cmd)
        page.keyboard.press("Enter")
        page.wait_for_timeout(700)
    page.wait_for_timeout(1200)

def v3(page):  # lab slider drag
    page.goto(BASE + "lab/")
    page.wait_for_timeout(900)
    box = page.locator("#cmp").bounding_box()
    cx, cy = box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5
    page.mouse.move(cx, cy)
    page.mouse.down()
    for pct in [0.7, 0.85, 0.6, 0.35, 0.2, 0.45, 0.55, 0.5]:
        page.mouse.move(box["x"] + box["width"] * pct, cy, steps=8)
        page.wait_for_timeout(260)
    page.mouse.up()
    page.wait_for_timeout(500)
    scroll_pass(page, 400, 220)

def v6(page):  # micro-interaction reel: nav, buttons, reticles, progress rail
    page.goto(BASE)
    page.wait_for_timeout(1000)
    for sel in ["nav a.t[href='/pro/']", "nav a.t[href='/personal/']", "nav a.t[href='/']"]:
        page.locator(sel).hover()
        page.wait_for_timeout(420)
    page.locator(".links .lnk:nth-child(2)").hover()
    page.wait_for_timeout(420)
    page.locator(".links .lnk.pri").hover()
    page.wait_for_timeout(420)
    page.evaluate("window.scrollTo({top: document.querySelector('.sec:nth-of-type(2)').offsetTop - 80, behavior:'instant'})")
    page.wait_for_timeout(900)
    cards = page.locator(".grid3 .card")
    for i in range(min(cards.count(), 3)):
        cards.nth(i).hover()
        page.wait_for_timeout(800)
        page.mouse.move(10, 500)
        page.wait_for_timeout(420)
    page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
    page.wait_for_timeout(600)
    page.evaluate("window.scrollTo({top: document.body.scrollHeight, behavior:'instant'})")
    page.wait_for_timeout(900)

def v7(page):  # mobile arrival
    pass  # viewport set by record()
    page.goto(BASE)
    page.wait_for_timeout(1000)
    scroll_pass(page, 400, 300)
    page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
    page.wait_for_timeout(600)
    page.locator(".links .lnk.pri").hover()
    page.wait_for_timeout(700)

def v4(page):  # view transitions across stations
    page.goto(BASE)
    page.wait_for_timeout(900)
    for path in ["/pro/", "/personal/", "/"]:
        page.evaluate(f"location.href = '{path}'")
        page.wait_for_timeout(1400)

def v5(page):  # dashboard: heatmap page switch + profile timeline
    import sqlite3, os, random, string
    key = os.environ.get("TELEMETRY_KEY", "testkey123")
    # seed a little extra traffic so the dashboard shows life
    page.goto(BASE)
    page.wait_for_timeout(600)
    page.goto(BASE + "dash-not-here", wait_until="domcontentloaded")
    page.goto(f"http://127.0.0.1:8819/dash?key={key}")
    page.wait_for_timeout(1500)
    sel = page.locator("#hpage")
    for opt in ["All options"]:
        pass
    opts = sel.locator("option")
    n = opts.count()
    for i in range(min(n, 4)):
        sel.select_option(index=i)
        page.wait_for_timeout(900)
    rows = page.locator("#vis tbody tr")
    if rows.count():
        rows.first.click()
        page.wait_for_timeout(1000)
    page.wait_for_timeout(600)

if __name__ == "__main__":
    import sys
    only = sys.argv[1] if len(sys.argv) > 1 else None
    jobs = {"v1-arrival-power-on": v1, "v2-console-session": v2, "v3-lab-instrument": v3,
            "v4-view-transitions": v4, "v5-station-telemetry": v5,
            "v6-microinteractions": v6, "v7-mobile-arrival": v7}
    for name, fn in jobs.items():
        if only and not name.startswith(only):
            continue
        try:
            vp = {"width": 390, "height": 844} if name == "v7-mobile-arrival" else None
            record(name, fn, 1.2, vp)
        except Exception as e:
            print("FAILED", name, e)
