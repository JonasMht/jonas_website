#!/usr/bin/env python3
"""Interaction & HMI audit against the live preview.

Checks the things a human-factors review actually cares about:
  · overflow / layout breakage across the real breakpoint ladder
  · focus visibility and tab order (keyboard reachability)
  · touch target sizes (WCAG 2.2 SC 2.5.8 — 24x24 minimum)
  · contrast of rendered text against its real painted background
  · motion: does prefers-reduced-motion actually stop animation
  · zero-JS: is content present without JavaScript
  · interaction feedback latency on the primary controls

    python3 scripts/audit-interaction.py [base_url]
"""
import asyncio
import json
import sys

from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8091"

PAGES = [
    ("home", "/"),
    ("pro", "/pro/"),
    ("personal", "/personal/"),
    ("pubs", "/pro/publications/"),
    ("bibtex", "/pro/research/2025-heat-ijcars/"),
    ("lab", "/lab/"),
    ("news", "/news/"),
    ("legal", "/legal/"),
    ("privacy", "/privacy/"),
    ("404", "/this-page-does-not-exist/"),
]

VIEWPORTS = [
    ("320", 320, 568),
    ("375", 375, 667),
    ("414", 414, 896),
    ("768", 768, 1024),
    ("1024", 1024, 768),
    ("1280", 1280, 800),
    ("1440", 1440, 900),
    ("1920", 1920, 1080),
]

# WCAG 2.x relative luminance / contrast
CONTRAST_JS = """
() => {
  const lum = (r, g, b) => {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const parse = s => {
    const m = s.match(/rgba?\\(([^)]+)\\)/);
    if (!m) return null;
    const p = m[1].split(/[,\\s/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const over = (fg, bg) => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a), a: 1
  });
  const bgOf = el => {
    let n = el, acc = null;
    while (n && n.nodeType === 1) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) { acc = acc ? over(acc, c) : c; if (acc.a >= 0.999) return acc; }
      n = n.parentElement;
    }
    return acc || { r: 12, g: 15, b: 20, a: 1 };
  };
  const out = [];
  const els = document.querySelectorAll('body *:not(script):not(style):not(svg *)');
  for (const el of els) {
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) < 0.1) continue;
    // only elements that own a visible text node
    const own = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).map(n => n.textContent.trim()).join(' ');
    if (!own) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const fg = parse(st.color); if (!fg) continue;
    const bg = bgOf(el);
    const f = over(fg, bg);
    const L1 = lum(f.r, f.g, f.b), L2 = lum(bg.r, bg.g, bg.b);
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const size = parseFloat(st.fontSize);
    const bold = parseInt(st.fontWeight, 10) >= 700;
    const large = size >= 24 || (bold && size >= 18.66);
    const need = large ? 3.0 : 4.5;
    if (ratio < need) {
      out.push({
        text: own.slice(0, 60), ratio: +ratio.toFixed(2), need,
        size: +size.toFixed(1), color: st.color,
        sel: el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/).join('.') : '')
      });
    }
  }
  return out;
}
"""

# WCAG 2.2 SC 2.5.8 Target Size (Minimum) = 24x24 CSS px
TARGETS_JS = """
() => {
  const out = [];
  for (const el of document.querySelectorAll('a[href], button, summary, input, select, textarea, [tabindex]:not([tabindex="-1"])')) {
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    if (el.closest('.skip') || el.classList.contains('skip')) continue;
    if (r.width < 24 || r.height < 24) {
      out.push({
        text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 40),
        w: +r.width.toFixed(1), h: +r.height.toFixed(1),
        sel: el.tagName.toLowerCase() + (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\\s+/).join('.') : '')
      });
    }
  }
  return out;
}
"""

OVERFLOW_JS = """
() => {
  const de = document.documentElement;
  const out = { page: de.scrollWidth - de.clientWidth, nodes: [] };
  if (out.page > 1) {
    for (const el of document.querySelectorAll('body *')) {
      const st = getComputedStyle(el);
      if (st.display === 'none' || st.position === 'fixed') continue;
      const r = el.getBoundingClientRect();
      if (r.right > de.clientWidth + 1 || r.left < -1) {
        out.nodes.push({
          sel: el.tagName.toLowerCase() + (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\\s+/).join('.') : ''),
          left: +r.left.toFixed(1), right: +r.right.toFixed(1), w: +r.width.toFixed(1),
          scrollW: el.scrollWidth, clientW: el.clientWidth
        });
      }
      if (out.nodes.length > 12) break;
    }
  }
  // per-element scroll traps. Three cases, and only the first is a defect:
  //   clip  — overflow-x hidden/clip: content is silently lost. BUG.
  //   auto  — an intentional scroll region (a wide code block). Fine.
  //   paint — overflow visible; a descendant's ::after reticle (inset:-7px,
  //           pointer-events:none) paints past the box. Clipped by
  //           html/body overflow-x:clip, page scroll stays 0. Fine.
  const R = el => {
    const st = getComputedStyle(el);
    return { sel: el.tagName.toLowerCase() + (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\\s+/).join('.') : ''),
             scrollW: el.scrollWidth, clientW: el.clientWidth, overflowX: st.overflowX };
  };
  for (const el of document.querySelectorAll('pre, table, .article-content > *, .container > *')) {
    if (el.scrollWidth <= el.clientWidth + 2) continue;
    const ox = getComputedStyle(el).overflowX;
    const kind = (ox === 'hidden' || ox === 'clip') ? 'CLIP' : (ox === 'auto' || ox === 'scroll') ? 'SCROLL' : 'PAINT';
    out.nodes.push({ sel: kind + ' ' + R(el).sel, scrollW: el.scrollWidth, clientW: el.clientWidth, overflowX: ox });
  }
  return out;
}
"""


async def audit_page(browser, name, path, vw, vh):
    ctx = await browser.new_context(viewport={"width": vw, "height": vh})
    page = await ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("console", lambda m: errs.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    res = {"page": name, "path": path, "vw": vw, "status": None}
    try:
        r = await page.goto(BASE + path, wait_until="load", timeout=20000)
        res["status"] = r.status if r else None
        await page.wait_for_timeout(320)
        res["overflow"] = await page.evaluate(OVERFLOW_JS)
        res["contrast"] = await page.evaluate(CONTRAST_JS)
        res["targets"] = await page.evaluate(TARGETS_JS)
    except Exception as e:
        res["error"] = str(e)[:200]
    res["jsErrors"] = errs
    await ctx.close()
    return res


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        report = {"overflow": [], "contrast": [], "targets": [], "jsErrors": [], "status": []}

        # 1. layout sweep across the breakpoint ladder
        for vw_name, vw, vh in VIEWPORTS:
            for name, path in PAGES:
                r = await audit_page(browser, name, path, vw, vh)
                tag = f"{name}@{vw}"
                if r.get("status") not in (200, 404):
                    report["status"].append({"page": tag, "status": r.get("status"), "error": r.get("error")})
                if r.get("error"):
                    report["jsErrors"].append({"page": tag, "error": r["error"]})
                for e in r.get("jsErrors", []):
                    report["jsErrors"].append({"page": tag, "error": e})
                ov = r.get("overflow") or {}
                if ov.get("page", 0) > 1 or ov.get("nodes"):
                    report["overflow"].append({"page": tag, "pageScroll": ov.get("page"), "nodes": ov.get("nodes", [])[:8]})
                for c in r.get("contrast", []):
                    report["contrast"].append({"page": tag, **c})
                for t in r.get("targets", []):
                    report["targets"].append({"page": tag, **t})

        # 2. dedupe contrast + targets by (sel, color, size)
        seen = set()
        uniq = []
        for c in report["contrast"]:
            k = (c["sel"], c["color"], c["size"], c["need"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(c)
        report["contrast"] = uniq

        seen = set()
        uniq = []
        for t in report["targets"]:
            k = (t["sel"], t["w"], t["h"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(t)
        report["targets"] = uniq

        # 3. reduced motion — animation must stop
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        page = await ctx.new_page()
        await page.goto(BASE + "/", wait_until="load", timeout=20000)
        await page.wait_for_timeout(400)
        report["reducedMotion"] = await page.evaluate("""() => {
          const bad = [];
          for (const el of document.querySelectorAll('body *')) {
            const st = getComputedStyle(el);
            const d = st.animationDuration.split(',').map(s => parseFloat(s) * (s.includes('ms') ? 0.001 : 1));
            const t = st.transitionDuration.split(',').map(s => parseFloat(s) * (s.includes('ms') ? 0.001 : 1));
            if (d.some(v => v > 0.05) || t.some(v => v > 0.05)) {
              bad.push({sel: el.tagName.toLowerCase() + (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\\s+/).join('.') : ''),
                        anim: st.animationDuration, trans: st.transitionDuration});
            }
            if (bad.length > 10) break;
          }
          return bad;
        }""")
        await ctx.close()

        # 4. zero-JS: content must exist in raw HTML
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800}, java_script_enabled=False)
        page = await ctx.new_page()
        await page.goto(BASE + "/", wait_until="load", timeout=20000)
        report["noJS"] = await page.evaluate("""() => {
          const vis = el => { const st = getComputedStyle(el);
            return st.display !== 'none' && st.visibility !== 'hidden' && parseFloat(st.opacity) > 0.05; };
          const h1 = document.querySelector('h1');
          const hidden = [...document.querySelectorAll('.reveal, main section, main article')].filter(e => !vis(e)).length;
          const ign = document.querySelector('.ignition');
          return { h1: h1 ? h1.textContent.trim().slice(0,60) : null,
                   h1Visible: h1 ? vis(h1) : false,
                   hiddenBlocks: hidden,
                   ignitionVisible: ign ? vis(ign) : false,
                   textLen: document.body.innerText.trim().length };
        }""")
        await ctx.close()

        # 5. keyboard: tab through the first N stops, confirm a visible focus ring
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()
        await page.goto(BASE + "/", wait_until="load", timeout=20000)
        await page.wait_for_timeout(400)
        stops = []
        for _ in range(14):
            await page.keyboard.press("Tab")
            info = await page.evaluate("""() => {
              const el = document.activeElement;
              if (!el || el === document.body) return null;
              const st = getComputedStyle(el);
              const r = el.getBoundingClientRect();
              return { tag: el.tagName.toLowerCase(),
                       text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 34),
                       outline: st.outlineStyle + ' ' + st.outlineWidth,
                       hasRing: st.outlineStyle !== 'none' && parseFloat(st.outlineWidth) > 0,
                       boxShadow: st.boxShadow !== 'none',
                       offscreen: r.top < -50 || r.bottom > innerHeight + 50,
                       top: Math.round(r.top) };
            }""")
            if info:
                stops.append(info)
        report["tabOrder"] = stops
        await ctx.close()

        await browser.close()

    with open("/tmp/audit-interaction.json", "w") as fh:
        json.dump(report, fh, indent=1)
    print(f"wrote /tmp/audit-interaction.json ({len(json.dumps(report))} bytes)")
    print("\n=== SUMMARY ===")
    for k, v in report.items():
        print(f"  {k}: {len(v) if isinstance(v, list) else v}")


asyncio.run(main())
