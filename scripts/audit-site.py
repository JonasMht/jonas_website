#!/usr/bin/env python3
"""Audit every built page in both themes, including narrow-screen layouts.

Requires Python Playwright and its Chromium browser. Start a server for public/
before running, for example: python3 -m http.server 8776 --directory public

    python3 scripts/audit-site.py http://127.0.0.1:8776
    python3 scripts/audit-site.py --paths / /pro/ --widths 320 1440

Failures include a selector, measured evidence and a screenshot. The audit uses
real layout and text geometry, so overflow hidden on the body cannot disguise
clipped content. Scrollable code/tables and links within running text are allowed.
It does not duplicate the command-console or main interaction audits.
"""

import argparse
import asyncio
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ROUTES = ("/", "/pro/", "/personal/", "/pro/publications/", "/pro/research/cnca-2025/", "/lab/")
HEIGHTS = {320: 780, 768: 1024, 1440: 1000}

# These are product-level controls, rather than links within sentences or lists.
CONTROL_SELECTOR = ",".join((
    "button", ".lnk", ".nav a.t", ".nav .sys", ".idrow > a", ".chiprow a",
    ".pager a", ".more", ".foot-next", ".hub-nav a", "summary", "[role='button']",
    "[role='slider']",
))

AUDIT_JS = r"""({touch, controlSelector, javascript}) => {
    const issues = [];
    const viewport = document.documentElement.clientWidth;
    const number = value => Number.parseFloat(value) || 0;
    const round = value => Math.round(value * 100) / 100;
    const style = element => getComputedStyle(element);
    const label = element => (element.getAttribute('aria-label') || element.textContent || element.alt || '')
        .trim().replace(/\s+/g, ' ').slice(0, 100);
    const selector = element => {
        if (element.id) return '#' + CSS.escape(element.id);
        const parts = [];
        for (let node = element; node && node !== document.body && parts.length < 5; node = node.parentElement) {
            if (node.id) { parts.unshift('#' + CSS.escape(node.id)); break; }
            let part = node.tagName.toLowerCase();
            const classes = [...node.classList].slice(0, 2);
            if (classes.length) part += '.' + classes.map(CSS.escape).join('.');
            if (node.parentElement) {
                const siblings = [...node.parentElement.children].filter(sibling => sibling.tagName === node.tagName);
                if (siblings.length > 1) part += ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')';
            }
            parts.unshift(part);
        }
        return parts.join(' > ');
    };
    const rectData = rect => ({left: round(rect.left), right: round(rect.right), top: round(rect.top + scrollY),
        bottom: round(rect.bottom + scrollY), width: round(rect.width), height: round(rect.height)});
    const visible = element => {
        if (!element.getClientRects().length || element.closest('svg, script, style, template, [hidden], [aria-hidden="true"]')) return false;
        if (element.closest('.sr-only, .visually-hidden, .skip:not(:focus)')) return false;
        const rect = element.getBoundingClientRect();
        if (rect.width < 1 || rect.height < 1) return false;
        for (let node = element; node; node = node.parentElement) {
            const s = style(node);
            if (s.display === 'none' || s.visibility === 'hidden' || s.visibility === 'collapse' || number(s.opacity) < .05) return false;
        }
        return true;
    };
    const add = (kind, element, detail) => issues.push({kind, selector: element ? selector(element) : 'html',
        text: element ? label(element) : '', ...detail});
    const scrollContainer = (element, axis) => {
        for (let node = element.parentElement; node && node !== document.body; node = node.parentElement) {
            const s = style(node);
            const overflow = axis === 'x' ? s.overflowX : s.overflowY;
            if (['auto', 'scroll'].includes(overflow)) return node;
        }
        return null;
    };
    const clippedBy = (element, rect, includeSelf = false) => {
        for (let node = includeSelf ? element : element.parentElement; node; node = node.parentElement) {
            const s = style(node);
            const bounds = node.getBoundingClientRect();
            const left = bounds.left + number(s.borderLeftWidth);
            const right = bounds.right - number(s.borderRightWidth);
            const top = bounds.top + number(s.borderTopWidth);
            const bottom = bounds.bottom - number(s.borderBottomWidth);
            const clipX = ['hidden', 'clip', 'auto', 'scroll'].includes(s.overflowX);
            const clipY = ['hidden', 'clip', 'auto', 'scroll'].includes(s.overflowY);
            const x = clipX && (rect.left < left - 1.5 || rect.right > right + 1.5);
            const y = clipY && (rect.top < top - 1.5 || rect.bottom > bottom + 1.5);
            if (x || y) return {ancestor: selector(node), x, y, overflow: s.overflow, bounds: rectData(bounds)};
        }
        return null;
    };
    const actualOverflow = document.documentElement.scrollWidth - viewport;
    if (actualOverflow > 1.5) add('page-overflow', null, {pixels: actualOverflow});

    const textElements = [];
    for (const element of document.querySelectorAll('body *')) {
        if (!visible(element)) continue;
        const bounds = element.getBoundingClientRect();
        if (!scrollContainer(element, 'x') && (bounds.left < -1.5 || bounds.right > viewport + 1.5)) {
            add('element-overflow', element, {rect: rectData(bounds), viewport});
        }
        const nodes = [...element.childNodes].filter(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
        if (!nodes.length) continue;
        textElements.push(element);
        // A code block/table can intentionally scroll; its container must still fit.
        if (scrollContainer(element, 'x')) continue;
        const s = style(element);
        if (s.textOverflow === 'ellipsis' || number(s.webkitLineClamp) > 0) continue;
        for (const node of nodes) {
            const range = document.createRange();
            range.selectNodeContents(node);
            let found = false;
            for (const rect of range.getClientRects()) {
                if (rect.width < 1 || rect.height < 1) continue;
                if (rect.left < -1.5 || rect.right > viewport + 1.5) {
                    add('text-overflow', element, {rect: rectData(rect), viewport}); found = true; break;
                }
                const clipped = clippedBy(element, rect, true);
                if (clipped && !scrollContainer(element, clipped.x ? 'x' : 'y')) {
                    add('clipped-text', element, {rect: rectData(rect), ...clipped}); found = true; break;
                }
            }
            if (found) break;
        }
    }

    const images = [...document.images].filter(visible);
    for (const image of images) {
        if (!image.complete || image.naturalWidth === 0) add('image-load', image, {url: image.currentSrc || image.src});
        const imageRect = image.getBoundingClientRect();
        if (!scrollContainer(image, 'x') && (imageRect.left < -1.5 || imageRect.right > viewport + 1.5)) {
            add('image-overflow', image, {rect: rectData(imageRect), viewport});
        }
        const frame = image.closest('.media-frame');
        if (!frame) { add('missing-image-frame', image, {url: image.currentSrc || image.src}); continue; }
        const before = getComputedStyle(frame, '::before');
        if (['none', 'normal'].includes(before.content) || before.display === 'none' || before.backgroundImage === 'none') {
            add('missing-frame-paint', frame, {}); continue;
        }
        const bounds = frame.getBoundingClientRect();
        const frameStyle = style(frame);
        const left = bounds.left + number(frameStyle.borderLeftWidth) + number(before.left);
        const top = bounds.top + number(frameStyle.borderTopWidth) + number(before.top);
        const rect = {left, top, width: number(before.width), height: number(before.height)};
        rect.right = rect.left + rect.width;
        rect.bottom = rect.top + rect.height;
        const clipped = clippedBy(frame, rect, true);
        if (clipped) add('clipped-image-frame', frame, {rect: rectData(rect), ...clipped});
    }

    for (const control of document.querySelectorAll(controlSelector)) {
        if (!visible(control)) continue;
        const rect = control.getBoundingClientRect();
        const isCopy = control.classList.contains('copy-btn');
        const minimum = !touch && isCopy ? 40 : 44;
        if (rect.height < minimum - .5 || rect.width < 24 - .5) {
            add('control-target', control, {width: round(rect.width), height: round(rect.height),
                minimumHeight: minimum, minimumWidth: 24});
        }
        if (!scrollContainer(control, 'x') && (rect.left < -1.5 || rect.right > viewport + 1.5)) {
            add('control-overflow', control, {rect: rectData(rect), viewport});
        }
    }

    const color = value => {
        const match = value.match(/^rgba?\(([^)]+)\)$/);
        if (!match) return null;
        const parts = match[1].split(/[\s,/]+/).filter(Boolean).map(Number);
        return {r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1};
    };
    const over = (fg, bg) => ({r: fg.r * fg.a + bg.r * (1 - fg.a),
        g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a), a: 1});
    const luminance = c => {
        const linear = v => { v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; };
        return .2126 * linear(c.r) + .7152 * linear(c.g) + .0722 * linear(c.b);
    };
    const background = element => {
        const layers = [];
        for (let node = element; node; node = node.parentElement) {
            const s = style(node);
            const c = color(s.backgroundColor);
            if (c && c.a > 0) layers.push(c);
            if (c && c.a >= .999) break;
        }
        let result = {r: 255, g: 255, b: 255, a: 1};
        for (const layer of layers.reverse()) result = over(layer, result);
        return result;
    };
    let contrastSamples = 0;
    for (const element of textElements) {
        // Text on photographs cannot be judged from a CSS background color.
        if (element.closest('.photo, .hub-hero__photo, .card__media, .spotlight__media, .paper-card .im, .slider, .yt-facade')) continue;
        const s = style(element);
        const fg = color(s.color);
        if (!fg || fg.a < .05 || s.webkitTextFillColor === 'transparent') continue;
        const bg = background(element);
        const effective = over(fg, bg);
        const a = luminance(effective), b = luminance(bg);
        const ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
        const size = number(s.fontSize), bold = number(s.fontWeight) >= 700;
        const required = size >= 24 || (size >= 18.66 && bold) ? 3 : 4.5;
        contrastSamples++;
        if (ratio + .015 < required) add('text-contrast', element, {ratio: round(ratio), required,
            fontSize: size, color: s.color, background: bg});
    }

    const fonts = [...document.fonts].map(font => ({family: font.family, weight: font.weight, status: font.status}));
    for (const font of fonts) if (font.status === 'error') add('font-load', null, font);
    for (const element of [document.body, document.querySelector('h1')].filter(Boolean)) {
        const s = style(element);
        const family = s.fontFamily.split(',')[0].trim().replace(/^["']|["']$/g, '').toLowerCase();
        const declared = fonts.filter(font => font.family.replace(/["']/g, '').toLowerCase() === family);
        if (declared.length && !declared.some(font => font.status === 'loaded')) add('font-not-rendered', element, {family});
    }
    const main = document.querySelector('main');
    const h1 = main && main.querySelector('h1');
    if (!main || !h1 || !visible(h1)) add('missing-main-content', main, {});
    else {
        const substantive = [...main.querySelectorAll('p, li, img, video, audio, canvas, table, pre, dl, form, blockquote, a[href]')]
            .some(element => visible(element) && !element.closest('header, nav, .pager')
                && (element.textContent.trim() || ['IMG', 'VIDEO', 'AUDIO', 'CANVAS'].includes(element.tagName)));
        if (!substantive) add('empty-main-content', main, {
            message: 'Only the heading/navigation is rendered; no useful page content or empty state.',
        });
    }
    if (!javascript) {
        for (const control of document.querySelectorAll('[data-theme-toggle], #console-toggle')) {
            if (visible(control)) add('no-js-inert-control', control, {});
        }
    }
    return {issues, fonts, images: images.length, framedImages: images.filter(image => image.closest('.media-frame')).length,
        contrastSamples, heading: h1 && h1.textContent.trim(), documentWidth: document.documentElement.scrollWidth,
        viewport, renderedTheme: document.documentElement.dataset.theme || 'dark'};
}"""


def discover_pages(public_dir):
    """Include rendered pages, but not Hugo redirects or the design-voting lab."""
    routes = []
    for file in sorted(public_dir.rglob("*.html")):
        relative = file.relative_to(public_dir)
        if relative.parts[0] == "opt":
            continue
        content = file.read_text(encoding="utf-8")
        if not re.search(r"<main(?:\s|>)", content, re.I):
            continue
        if re.search(r"<meta[^>]+http-equiv\s*=\s*['\"]?refresh", content, re.I):
            continue
        route = "/" + relative.as_posix()
        if route.endswith("/index.html"):
            route = route[:-10]
        routes.append(route)
    return routes


async def settle_page(page, javascript):
    """Scroll normally to load lazy images and reveal content before measuring."""
    await page.evaluate("document.fonts.ready")
    if not javascript:
        # With scripting disabled, Chromium does not invoke requestAnimationFrame
        # callbacks created by evaluate(). Drive scrolling from Python instead.
        height = await page.evaluate("document.documentElement.scrollHeight")
        step = max(300, int(page.viewport_size["height"] * .8))
        for offset in range(0, height, step):
            await page.evaluate("offset => scrollTo(0, offset)", offset)
            await page.wait_for_timeout(20)
        await page.evaluate("scrollTo(0, 0)")
        for _ in range(20):
            if await page.evaluate("[...document.images].every(image => image.complete)"):
                break
            await page.wait_for_timeout(100)
        await page.evaluate("document.fonts.ready")
        return
    await page.evaluate("""async () => {
        const pause = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const height = document.documentElement.scrollHeight;
        for (let y = 0; y < height; y += Math.max(300, innerHeight * .8)) {
            scrollTo(0, y);
            await pause();
        }
        scrollTo(0, 0);
        await pause();
    }""")
    await page.evaluate("""async () => {
        await Promise.race([
            Promise.all([...document.images].map(image => image.decode().catch(() => {}))),
            new Promise(resolve => setTimeout(resolve, 8000))
        ]);
        await document.fonts.ready;
    }""")


async def audit_page(page, args, route, width, theme, javascript, screenshot_budget):
    errors = []
    origin = urlsplit(args.base_url)

    def on_error(error):
        errors.append({"kind": "javascript-error", "message": str(error)})

    def on_response(response):
        target = urlsplit(response.url)
        if (target.scheme, target.netloc) == (origin.scheme, origin.netloc) and response.status >= 400:
            errors.append({"kind": "site-resource-http", "url": response.url, "status": response.status})

    def on_failed(request):
        target = urlsplit(request.url)
        if (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
            errors.append({"kind": "site-resource-failed", "url": request.url, "message": request.failure})

    page.on("pageerror", on_error)
    page.on("response", on_response)
    page.on("requestfailed", on_failed)
    result = {"path": route, "width": width, "theme": theme, "javascript": javascript}
    try:
        response = await page.goto(urljoin(args.base_url + "/", quote(route, safe="/")), wait_until="load", timeout=25000)
        result["status"] = response.status if response else None
        await settle_page(page, javascript)
        result.update(await page.evaluate(AUDIT_JS, {
            "touch": width <= 768, "controlSelector": CONTROL_SELECTOR, "javascript": javascript,
        }))
        if javascript and result["renderedTheme"] != theme:
            result["issues"].append({"kind": "theme-not-applied", "expected": theme, "actual": result["renderedTheme"]})
    except Exception as error:
        result["issues"] = [{"kind": "audit-error", "message": f"{type(error).__name__}: {error}"}]
    finally:
        result.setdefault("issues", []).extend(errors)
        page.remove_listener("pageerror", on_error)
        page.remove_listener("response", on_response)
        page.remove_listener("requestfailed", on_failed)

    if result["issues"] and screenshot_budget[0] > 0:
        screenshot_budget[0] -= 1
        name = re.sub(r"[^a-zA-Z0-9_-]+", "-", route.strip("/")) or "home"
        suffix = "js" if javascript else "no-js"
        path = args.output / "screenshots" / f"{name}-{width}-{theme}-{suffix}.png"
        try:
            issue = next((issue for issue in result["issues"] if issue.get("selector") not in (None, "html")), None)
            if issue:
                await page.locator(issue["selector"]).first.scroll_into_view_if_needed(timeout=1500)
            await page.screenshot(path=str(path), animations="disabled", timeout=8000)
            result["screenshot"] = str(path)
        except Exception as error:
            result["screenshotError"] = str(error)
    return result


async def run(args):
    routes = args.paths or discover_pages(args.public_dir)
    if not routes:
        raise ValueError(f"No rendered pages with <main> found in {args.public_dir}; build Hugo first.")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "screenshots").mkdir(exist_ok=True)
    samples = [] if args.skip_no_js else [route for route in SAMPLE_ROUTES if route in routes]
    total = len(routes) * len(args.widths) * len(args.themes) + len(samples)
    completed = 0
    results = []
    screenshot_budget = [args.max_screenshots]
    start = time.monotonic()
    print(f"Auditing {len(routes)} pages, {total} page configurations, {args.workers} browser workers.", flush=True)
    async with async_playwright() as playwright:
        browser = await getattr(playwright, args.browser).launch()

        async def batch(width, theme, javascript, paths):
            nonlocal completed
            context = await browser.new_context(
                viewport={"width": width, "height": HEIGHTS.get(width, 900)},
                reduced_motion="reduce", has_touch=width <= 768, java_script_enabled=javascript,
            )
            if javascript:
                await context.add_init_script("localStorage.setItem('jm.theme', " + json.dumps(theme) + ");")
            queue = asyncio.Queue()
            for route in paths:
                queue.put_nowait(route)
            print(f"  {width}px · {theme} · {'JavaScript' if javascript else 'no JavaScript'}", flush=True)

            async def worker():
                nonlocal completed
                page = await context.new_page()
                while not queue.empty():
                    route = queue.get_nowait()
                    result = await audit_page(page, args, route, width, theme, javascript, screenshot_budget)
                    results.append(result)
                    completed += 1
                    if result["issues"]:
                        counts = Counter(issue["kind"] for issue in result["issues"])
                        print(f"    FAIL {route} · " + ", ".join(f"{name}:{count}" for name, count in counts.items()), flush=True)
                    elif completed % 10 == 0 or completed == total:
                        print(f"    {completed}/{total} checked", flush=True)
                    queue.task_done()
                await page.close()

            await asyncio.gather(*(worker() for _ in range(min(args.workers, len(paths)))))
            await context.close()

        for width in args.widths:
            for theme in args.themes:
                await batch(width, theme, True, routes)
        if samples:
            await batch(390, "dark", False, samples)
        await browser.close()

    counts = Counter(issue["kind"] for result in results for issue in result["issues"])
    failed = sum(bool(result["issues"]) for result in results)
    report = {"baseURL": args.base_url, "publicDirectory": str(args.public_dir), "routes": routes,
        "elapsedSeconds": round(time.monotonic() - start, 1), "configurations": len(results),
        "failedConfigurations": failed, "issueCounts": dict(counts), "results": results}
    report_path = args.output / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = [f"{len(results) - failed}/{len(results)} configurations passed in {report['elapsedSeconds']} seconds."]
    for kind, count in sorted(counts.items()):
        summary.append(f"\n{kind}: {count}")
        examples = [(result, issue) for result in results for issue in result["issues"] if issue["kind"] == kind]
        for result, issue in examples[:5]:
            summary.append(f"  {result['path']} {result['width']}px {result['theme']}: " + json.dumps(issue, ensure_ascii=False))
    summary.append(f"\nFull report: {report_path}")
    summary_text = "\n".join(summary) + "\n"
    (args.output / "summary.txt").write_text(summary_text, encoding="utf-8")
    print(summary_text, flush=True)
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base_url", nargs="?", default="http://127.0.0.1:8776")
    parser.add_argument("--public-dir", type=Path, default=ROOT / "public")
    parser.add_argument("--output", type=Path, default=Path("/tmp/website-site-audit"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--widths", type=int, nargs="+", default=[320, 768, 1440])
    parser.add_argument("--themes", nargs="+", choices=["dark", "light"], default=["dark", "light"])
    parser.add_argument("--paths", nargs="+", help="Audit specific routes instead of discovering every rendered page.")
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default="chromium")
    parser.add_argument("--skip-no-js", action="store_true")
    parser.add_argument("--max-screenshots", type=int, default=120)
    args = parser.parse_args()
    if args.workers < 1 or any(width < 240 for width in args.widths):
        parser.error("workers must be positive and viewport widths at least 240px")
    args.base_url = args.base_url.rstrip("/")
    try:
        return asyncio.run(run(args))
    except (KeyboardInterrupt, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
