#!/usr/bin/env python3
"""Exercise the real console UI, navigation and telemetry controls in a browser.

Usage: python3 scripts/audit-console.py [base_url] [artifact_directory] [browser]
Browser is chromium (default), firefox or webkit; it must already be installed.
The configured-telemetry tests intercept /e locally; they send no real analytics.
"""

import asyncio
import json
import pathlib
import sys

from playwright.async_api import async_playwright, expect


BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8776").rstrip("/")
ARTIFACTS = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/website-console-audit")
BROWSER = sys.argv[3] if len(sys.argv) > 3 else "chromium"


async def command(page, text, expected=None):
    field = page.locator("#console-input")
    await field.fill(text)
    await field.press("Enter")
    if expected:
        await expect(page.locator(".console__entry").last).to_contain_text(expected)


async def open_console(page):
    await page.locator("#console-toggle").click()
    await expect(page.locator("#console")).to_be_visible()
    await expect(page.locator("#console-input")).to_be_focused()


async def assert_geometry(page):
    issues = await page.evaluate("""() => {
        const box = document.querySelector('#console');
        const rect = box.getBoundingClientRect();
        const bad = [];
        if (rect.left < -1 || rect.right > innerWidth + 1 || rect.top < -1 || rect.bottom > innerHeight + 1)
            bad.push({element: 'dialog', rect: rect.toJSON(), viewport: [innerWidth, innerHeight]});
        for (const el of box.querySelectorAll('button, input, .console__body, .console__result')) {
            const r = el.getBoundingClientRect();
            if (!r.width || !r.height) continue;
            if (r.left < rect.left - 1 || r.right > rect.right + 1 || el.scrollWidth > el.clientWidth + 2)
                bad.push({element: el.className || el.tagName, overflow: el.scrollWidth - el.clientWidth});
            if (el.matches('button') && (r.width < 24 || r.height < 24))
                bad.push({element: el.className, target: [r.width, r.height]});
        }
        const input = box.querySelector('input').getBoundingClientRect();
        if (input.bottom > rect.bottom || input.top < rect.top)
            bad.push({element: 'input', clipped: true});
        return bad;
    }""")
    assert not issues, json.dumps(issues)


async def interaction_checks(browser):
    context = await browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    await page.goto(BASE + "/", wait_until="networkidle")
    await open_console(page)
    await expect(page.locator(".console__run")).to_be_disabled()
    await command(page, "help", "find <words>")
    await expect(page.locator(".console__help dt")).to_have_count(7)
    await page.screenshot(path=str(ARTIFACTS / "desktop-help.png"), animations="disabled")

    await command(page, "FiNd games", "matching")
    await expect(page.locator(".console__entry").last.locator(".console__result").first).to_be_visible()
    search_link = page.locator(".console__entry").last.locator(".console__result").first
    destination = await search_link.get_attribute("href")
    await search_link.click()
    await page.wait_for_url(BASE + destination)
    await open_console(page)
    await command(page, "session", "Commands run on this page: 1")

    field = page.locator("#console-input")
    await field.fill("unfinished search")
    await field.press("ArrowUp")
    await expect(field).to_have_value("session")
    await field.press("ArrowDown")
    await expect(field).to_have_value("unfinished search")
    await field.fill("hel")
    await field.press("ArrowRight")
    await expect(field).to_have_value("help")
    await field.press("Tab")
    await expect(page.locator(".console__run")).to_be_focused()
    for _ in range(14):
        await page.keyboard.press("Tab")
        # Native dialogs allow focus to visit browser chrome (reported as body),
        # while every page control behind the dialog remains inert.
        assert await page.evaluate("document.activeElement === document.body || document.querySelector('#console').contains(document.activeElement)")

    await command(page, "unrecognized <img src=x onerror=alert(1)>", "Unknown command")
    assert await page.locator("#console img").count() == 0
    for path in ["//example.com", "https://example.com", "\\\\example.com", "/page-that-does-not-exist/"]:
        await command(page, "goto " + path)
        await expect(page.locator(".console__entry").last).to_contain_text(
            "No page at" if path.startswith("/page-") else "Use a page on this site"
        )
        assert page.url == BASE + destination

    await command(page, "find impossible-string-9a45d", "No pages found")
    await command(page, "telemetry", "not configured")
    await command(page, "telemetry off", "saved preference: off")
    assert await page.evaluate("localStorage.getItem('jm.telemetry')") == "off"
    await command(page, "telemetry on", "allow telemetry when configured")
    await page.evaluate("localStorage.setItem('jm.console.v1', JSON.stringify({pages:['legacy']})); localStorage.setItem('jm.theme', 'light')")
    await command(page, "clear", "Console output and history cleared")
    assert await page.locator(".console__entry").count() == 1
    assert await page.evaluate("localStorage.getItem('jm.console.v1')") is None
    assert await page.evaluate("localStorage.getItem('jm.theme')") == "light"
    await field.press("ArrowUp")
    await expect(field).to_have_value("")

    await page.keyboard.press("Escape")
    await expect(page.locator("#console")).not_to_be_visible()
    await expect(page.locator("#console-toggle")).to_be_focused()
    await page.wait_for_function("!document.body.classList.contains('console-open')")
    for _ in range(3):
        await page.keyboard.press("Backquote")
        await expect(field).to_be_focused()
        await page.locator("[data-console-close]").click()
        await expect(page.locator("#console-toggle")).to_be_focused()

    await open_console(page)
    await command(page, "goto pro")
    await page.wait_for_url(BASE + "/pro/")
    await open_console(page)
    await command(page, "goto /personal")
    await page.wait_for_url(BASE + "/personal/")
    await open_console(page)
    await command(page, "goto /pro/research/cnca-2025/")
    await page.wait_for_url(BASE + "/pro/research/cnca-2025/")
    assert not errors, errors
    await context.close()
    return "Commands, linked search, internal navigation, safe text, history, completion, focus, clear and persistence"


async def failure_checks(browser):
    context = await browser.new_context(reduced_motion="reduce")
    page = await context.new_page()
    await page.route("**/searchindex.json", lambda route: route.fulfill(status=503, body="Unavailable"))
    await page.goto(BASE + "/", wait_until="networkidle")
    await open_console(page)
    await command(page, "find research", "Search is unavailable")
    await expect(page.locator(".console__entry").last.get_by_role("button", name="Try again")).to_be_visible()
    await page.unroute("**/searchindex.json")
    await page.locator(".console__entry").last.get_by_role("button", name="Try again").click()
    await expect(page.locator(".console__entry").last).to_contain_text("matching")
    await context.close()

    context = await browser.new_context(reduced_motion="reduce")
    await context.add_init_script("""Storage.prototype.getItem = function() { throw new DOMException('Blocked', 'SecurityError'); };
        Storage.prototype.setItem = function() { throw new DOMException('Blocked', 'SecurityError'); };
        Storage.prototype.removeItem = function() { throw new DOMException('Blocked', 'SecurityError'); };""")
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    await page.goto(BASE + "/", wait_until="networkidle")
    await open_console(page)
    await command(page, "telemetry off", "Browser storage is unavailable")
    await command(page, "clear", "Console output and history cleared")
    await command(page, "find games", "matching")
    assert not errors, errors
    await context.close()

    context = await browser.new_context(java_script_enabled=False)
    page = await context.new_page()
    await page.goto(BASE + "/", wait_until="networkidle")
    await expect(page.locator("#console-toggle")).not_to_be_visible()
    await expect(page.locator("#console")).not_to_be_visible()
    await expect(page.locator("main h1")).to_be_visible()
    await context.close()
    return "Failed search/retry, blocked browser storage and JavaScript-disabled fallback"


async def telemetry_checks(browser):
    async def fixture(context):
        if BROWSER == "webkit":
            # WebKit's interception API omits Blob beacon bodies. Exercise the
            # real fetch fallback so the payload remains inspectable in this test.
            await context.add_init_script("navigator.sendBeacon = () => false;")
        # Keep the real navigation response and its security/address-space
        # context. Fulfilling synthetic HTML for an HTTP LAN preview makes
        # Chromium block its real subresources as private-network requests.
        # Configure only the deferred collector script before it executes.
        await context.add_init_script("""(() => {
            function configure() {
                const script = document.querySelector('script[data-telemetry]');
                if (!script) return false;
                script.dataset.telemetry = '/e';
                return true;
            }
            const observer = new MutationObserver(() => {
                if (configure()) observer.disconnect();
            });
            observer.observe(document, {childList: true, subtree: true});
            if (configure()) observer.disconnect();
        })();""")
        batches = []

        async def receive(route):
            batches.extend(json.loads(route.request.post_data))
            await route.fulfill(status=204)

        await context.route("**/e", receive)
        return batches

    context = await browser.new_context(reduced_motion="reduce")
    batches = await fixture(context)
    page = await context.new_page()
    await page.clock.install()
    await page.goto(BASE + "/", wait_until="networkidle")
    await open_console(page)
    await command(page, "telemetry", "Site telemetry is on")
    assert await page.evaluate("Boolean(localStorage.getItem('jm.visitor.v1') && sessionStorage.getItem('jm.session.v1'))")
    await command(page, "telemetry off", "Site telemetry is off")
    assert await page.evaluate("localStorage.getItem('jm.visitor.v1') === null && sessionStorage.getItem('jm.session.v1') === null")
    await page.clock.fast_forward(6000)
    assert not batches, batches
    await command(page, "telemetry on", "Site telemetry is on")
    await command(page, "find games", "matching")
    await page.clock.fast_forward(6000)
    await page.wait_for_timeout(100)
    assert len(batches) == 1 and batches[0]["t"] == "pv", batches
    assert "games" not in json.dumps(batches)

    # An opt-out in another tab must also stop this tab's collector.
    second = await context.new_page()
    await second.goto(BASE + "/", wait_until="networkidle")
    await open_console(second)
    await command(second, "telemetry off", "Site telemetry is off")
    await command(page, "telemetry", "Site telemetry is off")
    await context.close()

    context = await browser.new_context(reduced_motion="reduce")
    await context.add_init_script("Object.defineProperty(navigator, 'doNotTrack', {get: () => '1'});")
    batches = await fixture(context)
    page = await context.new_page()
    await page.clock.install()
    await page.goto(BASE + "/", wait_until="networkidle")
    await open_console(page)
    await command(page, "telemetry on", "browser sends Do Not Track")
    await page.clock.fast_forward(6000)
    assert not batches, batches
    assert await page.evaluate("localStorage.getItem('jm.visitor.v1')") is None
    await context.close()
    return "Configured telemetry: queued-event discard, ID removal, immediate re-enable, no console tracking, cross-tab opt-out and Do Not Track"


async def layout_checks(browser):
    sizes = [(320, 568), (390, 844), (768, 1024), (1024, 768), (1440, 900), (844, 390), (320, 320)]
    for width, height in sizes:
        for theme in ["dark", "light"]:
            context = await browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce", has_touch=width < 800)
            await context.add_init_script(f"localStorage.setItem('jm.theme', '{theme}');")
            page = await context.new_page()
            await page.goto(BASE + "/personal/", wait_until="networkidle")
            if width < 800:
                await page.locator("#console-toggle").tap()
                await expect(page.locator("#console-input")).to_be_focused()
            else:
                await open_console(page)
            await command(page, "help", "find <words>")
            await assert_geometry(page)
            if width < 800:
                await page.locator("#console-input").fill("session")
                await page.locator(".console__run").tap()
                await expect(page.locator(".console__entry").last).to_contain_text("Commands run on this page: 2")
            await command(page, "find research", "matching")
            await assert_geometry(page)
            await page.locator("#console-input").fill("goto /pro/")
            await assert_geometry(page)
            assert await page.locator("#console").evaluate("el => getComputedStyle(el).animationName") == "none"
            if width in [320, 390, 844, 1440]:
                await page.screenshot(path=str(ARTIFACTS / f"console-{width}x{height}-{theme}.png"), animations="disabled")
            if width < 800:
                await page.locator("[data-console-close]").tap()
            else:
                await page.locator("[data-console-close]").click()
            await expect(page.locator("#console")).not_to_be_visible()
            await context.close()
    return f"{len(sizes) * 2} responsive layouts: 320px through 1440px, portrait/landscape, light/dark, reduced motion and touch close"


async def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    results = []
    async with async_playwright() as playwright:
        if BROWSER not in ["chromium", "firefox", "webkit"]:
            raise ValueError(f"Unsupported browser: {BROWSER}")
        browser = await getattr(playwright, BROWSER).launch()
        for check in [interaction_checks, failure_checks, telemetry_checks, layout_checks]:
            result = await check(browser)
            results.append({"check": check.__name__, "browser": BROWSER, "status": "passed", "coverage": result})
            print(json.dumps(results[-1]), flush=True)
        await browser.close()
    (ARTIFACTS / "report.json").write_text(json.dumps(results, indent=2) + "\n")
    print(f"Console audit passed. Artifacts: {ARTIFACTS}")


if __name__ == "__main__":
    asyncio.run(main())
