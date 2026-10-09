#!/usr/bin/env python3
"""Browser regressions for theme, clipboard, images, video facade and comparison controls.

Usage: python3 scripts/audit-controls.py [base_url] [artifact_directory]
Requires Python Playwright and its Chromium browser.
"""
import asyncio
import json
from pathlib import Path
import sys

from playwright.async_api import async_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8776").rstrip("/")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/website-controls-audit")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            reduced_motion="reduce",
            permissions=["clipboard-read", "clipboard-write"],
        )
        await context.add_init_script("localStorage.setItem('jm.telemetry', 'off')")
        page = await context.new_page()
        page.set_default_timeout(10000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        # Keyboard and pointer activation, icon feedback and persisted preference.
        await page.goto(BASE + "/", wait_until="networkidle")
        button = page.get_by_role("button", name="Switch to light mode")
        await button.focus()
        assert await button.evaluate("e => getComputedStyle(e).outlineStyle !== 'none'")
        await page.keyboard.press("Enter")
        assert await page.locator("html").get_attribute("data-theme") == "light"
        assert await page.locator(".theme-icon--moon").evaluate("e => getComputedStyle(e).opacity") == "1"
        await page.get_by_role("navigation", name="Main navigation").get_by_role("link", name="Personal", exact=True).click()
        await page.wait_for_url("**/personal/")
        await page.reload(wait_until="networkidle")
        assert await page.locator("html").get_attribute("data-theme") == "light"
        await page.get_by_role("button", name="Switch to dark mode").focus()
        await page.keyboard.press("Space")
        assert await page.locator("html").get_attribute("data-theme") == "dark"
        results.append("theme: keyboard, visible icon and persistence across navigation/reload")

        # Copy the actual citation including its indentation and line breaks.
        await page.goto(BASE + "/pro/research/2025-heat-ijcars/", wait_until="networkidle")
        code = page.locator(".highlight").first
        expected = (await code.locator("pre").inner_text()).rstrip("\n")
        copy = code.get_by_role("button", name="Copy to clipboard")
        await copy.click()
        assert await page.evaluate("navigator.clipboard.readText()") == expected
        assert (await copy.text_content()).strip() == "Copied"
        assert await page.locator('[aria-live="polite"]').filter(has_text="Copied to clipboard").count()
        doi_copy = page.get_by_role("button", name="Copy DOI:").first
        await doi_copy.click()
        assert (await page.evaluate("navigator.clipboard.readText()")).startswith("10.")
        results.append("clipboard: exact multiline citation and DOI copied")

        # Denied clipboard permission uses the fallback and restores keyboard focus.
        await page.evaluate("Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText:()=>Promise.reject(new Error('denied'))}})")
        await copy.focus()
        await page.keyboard.press("Enter")
        assert await copy.evaluate("e => e === document.activeElement")
        assert await page.evaluate("window.getSelection().toString()") == ""
        await page.evaluate("document.execCommand = () => false")
        await copy.click()
        await page.wait_for_function("document.querySelector('.highlight .copy-btn').textContent.includes('Try again')")
        results.append("clipboard: denied API fallback, focus restoration and explicit failure feedback")

        # Pointer drag and keyboard must continue from the same seam position.
        await page.goto(BASE + "/lab/", wait_until="networkidle")
        slider = page.get_by_role("slider", name="Comparison seam position")
        box = await page.locator("#cmp").bounding_box()
        await page.mouse.move(box["x"] + .8 * box["width"], box["y"] + .5 * box["height"])
        await page.mouse.down()
        await page.mouse.up()
        before = int(await slider.get_attribute("aria-valuenow"))
        assert 79 <= before <= 81
        await slider.press("ArrowRight")
        after = int(await slider.get_attribute("aria-valuenow"))
        assert after == before + 2, (before, after)
        await slider.press("Home")
        assert await slider.get_attribute("aria-valuenow") == "0"
        await slider.press("End")
        assert await slider.get_attribute("aria-valuenow") == "100"
        await slider.press("PageDown")
        assert await slider.get_attribute("aria-valuenow") == "90"
        results.append("comparison: drag, keyboard continuity, Home/End and page steps")

        # A real iframe appears only after the visitor activates the preview.
        # Fulfil the embed locally so the test never contacts YouTube's player.
        await context.route("https://www.youtube-nocookie.com/**", lambda route: route.fulfill(body="<title>Video fixture</title>"))
        await page.goto(BASE + "/personal/projects/project-notre-dame/", wait_until="domcontentloaded")
        assert await page.locator(".yt-facade iframe").count() == 0
        facade = page.get_by_role("button", name="Play the YouTube video").first
        await facade.focus()
        await page.keyboard.press("Enter")
        assert await page.locator(".yt-facade iframe").count() == 1
        results.append("video: keyboard activation, deferred player, no test-time third-party embed")
        assert not errors, errors
        await context.close()

        # Phone hit areas and touch comparison; no hover is needed for frames.
        context = await browser.new_context(
            viewport={"width": 390, "height": 844}, is_mobile=True,
            has_touch=True, reduced_motion="reduce",
        )
        await context.add_init_script("localStorage.setItem('jm.telemetry','off')")
        page = await context.new_page()
        await page.goto(BASE + "/pro/", wait_until="networkidle")
        await page.get_by_role("button", name="Switch to light mode").tap()
        controls = await page.locator(".lnk, [data-theme-toggle], .idrow > a").evaluate_all(
            "els => els.map(e=>({label:e.textContent.trim() || e.getAttribute('aria-label'),width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}))"
        )
        assert all(control["height"] >= 44 and control["width"] >= 44 for control in controls), controls
        await page.screenshot(path=str(OUT / "phone-controls.png"), animations="disabled")
        await page.goto(BASE + "/lab/", wait_until="networkidle")
        box = await page.locator("#cmp").bounding_box()
        await page.touchscreen.tap(box["x"] + box["width"] * .25, box["y"] + box["height"] * .5)
        value = int(await page.get_by_role("slider").get_attribute("aria-valuenow"))
        assert 24 <= value <= 26, value
        results.append("touch: 44px controls, theme switch and comparison interaction")
        await context.close()
        await browser.close()

    report = {"passed": results, "errors": []}
    (OUT / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
