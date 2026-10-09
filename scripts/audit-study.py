#!/usr/bin/env python3
"""Exercise the private design study, including background-only grain rendering.

Usage: python3 scripts/audit-study.py [base_url] [browser]
Requires Playwright. Run hero-options.py after building Hugo first.
"""

import asyncio
import json
import sys
from pathlib import Path
from runpy import run_path
from urllib.parse import parse_qs, urlsplit

from playwright.async_api import async_playwright


BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8776").rstrip("/")
ENGINE = sys.argv[2] if len(sys.argv) > 2 else "chromium"
PRESETS = json.loads(
    (
        Path(__file__).resolve().parents[1] / "design-lab/retrofuturism/presets.json"
    ).read_text()
)
LAYOUT_AUDIT = run_path(str(Path(__file__).with_name("audit-site.py")))


async def clipped(page, selector, inset=16, height=None):
    box = await page.locator(selector).bounding_box()
    clip = {
        "x": box["x"] + inset,
        "y": box["y"] + inset,
        "width": box["width"] - inset * 2,
        "height": min(height or box["height"], box["height"] - inset * 2),
    }
    return await page.screenshot(clip=clip, animations="disabled")


async def main():
    passed = []
    errors = []
    async with async_playwright() as p:
        browser = await getattr(p, ENGINE).launch()
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1080}, reduced_motion="reduce"
        )
        await context.add_init_script("localStorage.setItem('jm.telemetry', 'off')")
        page = await context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(BASE + "/opt/?v=blueprint&theme=dark", wait_until="networkidle")
        styles = []
        for version in PRESETS:
            await page.locator(".study-browse summary").click()
            await page.locator('[data-study-pane="backgrounds"]').click()
            button = page.locator(f'[data-preset="{version}"]')
            await button.focus()
            await page.keyboard.press("Enter")
            assert await button.get_attribute("aria-pressed") == "true"
            assert await page.locator('[data-preset][aria-pressed="true"]').count() == 1
            styles.append(
                await page.locator(".hub-hero").evaluate(
                    "e => getComputedStyle(e).backgroundColor"
                )
            )
            assert parse_qs(urlsplit(page.url).query)["v"] == [version]
            assert not await page.locator(".study-browse").evaluate("e => e.open")
        assert len(set(styles)) == len(PRESETS)
        await page.get_by_role("button", name="Next design", exact=True).click()
        assert await page.locator("html").get_attribute("data-study") == "blueprint"
        await page.get_by_role("button", name="Previous design", exact=True).click()
        assert await page.locator("html").get_attribute("data-study") == "solar"
        await page.locator(".study-browse summary").click()
        await page.locator(".study-adjust summary").focus()
        for _ in range(3):
            await page.keyboard.press("Tab")
        assert await page.locator(".site-header .sys").evaluate(
            "e => e === document.activeElement"
        )
        assert not await page.locator(".study-browse").evaluate("e => e.open")
        await page.locator(".study-browse summary").click()
        await page.locator("[data-study-preset]").select_option("ion")
        assert not await page.locator(".study-browse").evaluate("e => e.open")
        passed.append(
            f"{len(PRESETS)} distinct presets: gallery keyboard activation, selected state, wraparound stepping and URL"
        )

        # Every new geometry responds to its density control, including equal spacing
        # across different designs (which must not retain the previous vector path).
        for version, preset in PRESETS.items():
            if preset["round"] != 2:
                continue
            await page.locator("[data-study-preset]").select_option(version)
            await page.locator(".study-adjust summary").click()
            await page.locator("#study-grid").press("Home")
            sparse = await page.locator(".study-perspective path").first.get_attribute(
                "d"
            )
            await page.locator("#study-grid").press("End")
            assert sparse != await page.locator(
                ".study-perspective path"
            ).first.get_attribute("d")
            assert await page.locator(".study-perspective").first.is_visible()
            await page.keyboard.press("Escape")
        passed.append("all six new geometries redraw when grid spacing changes")

        await page.locator("[data-study-preset]").select_option("light-grid")
        await page.locator(".study-adjust summary").click()
        for key, last in (("grain", "35"), ("grid", "80"), ("glow", "160")):
            await page.locator(f"#study-{key}").focus()
            await page.keyboard.press("End")
            await page.wait_for_function(
                "([key, value]) => new URL(location.href).searchParams.get(key) === value",
                arg=[key, last],
            )
            assert await page.locator(f"#study-{key}").input_value() == last
        grid_before = await page.locator(".study-perspective path").first.get_attribute(
            "d"
        )
        await page.locator("#study-grid").press("Home")
        assert grid_before != await page.locator(
            ".study-perspective path"
        ).first.get_attribute("d")
        await page.locator("[data-study-theme]").click()
        assert await page.locator("html").get_attribute("data-theme") == "light"
        await page.reload(wait_until="networkidle")
        assert await page.locator("#study-grain").input_value() == "35"
        assert await page.locator("#study-grid").input_value() == "24"
        assert await page.locator("html").get_attribute("data-theme") == "light"
        await (
            page.get_by_role("navigation", name="Main navigation")
            .get_by_role("link", name="Professional", exact=True)
            .click()
        )
        await page.wait_for_url("**/opt/pro/**")
        assert await page.locator("html").get_attribute("data-study") == "light-grid"
        assert await page.locator("#study-grain").input_value() == "35"
        await page.locator(".study-adjust summary").click()
        await page.locator("#study-page").select_option("/opt/personal/")
        await page.wait_for_url("**/opt/personal/**")
        assert await page.locator("#study-glow").input_value() == "160"
        await page.locator(".study-adjust summary").click()
        await page.locator("[data-study-reset]").click()
        assert await page.locator("#study-grain").input_value() == "18"
        assert await page.locator("#study-grid").input_value() == "48"
        assert await page.locator("#study-glow").input_value() == "105"
        passed.append(
            "grain/grid/glow: keyboard ranges, rendered geometry, theme, reload, navigation and reset"
        )

        # Clipboard failure must explain how to recover and retain keyboard focus.
        await page.evaluate(
            "Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText:()=>Promise.reject(new Error('denied'))}}); document.execCommand = () => false"
        )
        await page.locator("[data-study-copy]").click()
        assert "Copy the address" in await page.locator(".study-message").inner_text()
        assert await page.locator("[data-study-copy]").evaluate(
            "e => e === document.activeElement"
        )
        await page.keyboard.press("Escape")
        assert not await page.locator(".study-adjust").evaluate("e => e.open")
        passed.append(
            "clipboard denial recovery, focus restoration and Escape dismissal"
        )

        # Grain must change actual backdrop pixels, while foreground pixels stay identical.
        await page.goto(
            BASE + "/opt/?v=light-grid&theme=dark", wait_until="networkidle"
        )
        await page.evaluate("document.fonts.ready")
        main_box = await page.locator(".page-surface").bounding_box()
        background_clip = {"x": 620, "y": main_box["y"] + 4, "width": 200, "height": 20}
        await page.evaluate(
            "document.documentElement.style.setProperty('--grain-opacity', '0')"
        )
        clean_background = await page.screenshot(clip=background_clip)
        clean_hero = await clipped(page, ".hub-hero__body")
        clean_header = await clipped(page, ".site-header")
        await page.evaluate(
            "document.documentElement.style.setProperty('--grain-opacity', '.35')"
        )
        assert clean_background != await page.screenshot(clip=background_clip)
        assert clean_hero == await clipped(page, ".hub-hero__body")
        assert clean_header == await clipped(page, ".site-header")
        await page.locator(".site-footer").scroll_into_view_if_needed()
        grain_footer = await clipped(page, ".site-footer")
        await page.evaluate(
            "document.documentElement.style.setProperty('--grain-opacity', '0')"
        )
        assert grain_footer == await clipped(page, ".site-footer")
        await page.goto(
            BASE + "/opt/pro/research/cnca-2025/?v=light-grid&theme=dark",
            wait_until="networkidle",
        )
        await page.evaluate("document.fonts.ready")
        await page.evaluate(
            "document.documentElement.style.setProperty('--grain-opacity', '0')"
        )
        clean_article = await clipped(page, ".post", height=400)
        await page.evaluate(
            "document.documentElement.style.setProperty('--grain-opacity', '.35')"
        )
        assert clean_article == await clipped(page, ".post", height=400)
        passed.append(
            "pixel comparison: grain changes background only; hero, photo, header, footer and article remain identical"
        )

        await page.set_viewport_size({"width": 320, "height": 780})
        await page.goto(BASE + "/opt/?v=afterglow&theme=dark", wait_until="networkidle")
        await page.locator("[data-study-preset]").select_option("vector")
        assert await page.locator("html").get_attribute("data-study") == "vector"
        await page.locator(".study-browse summary").click()
        await page.locator('[data-study-pane="backgrounds"]').click()
        await page.locator('[data-preset="solar"]').click()
        assert await page.locator("html").get_attribute("data-study") == "solar"
        await page.locator(".study-browse summary").click()
        await page.locator(".study-adjust summary").click()
        assert not await page.locator(".study-browse").evaluate("e => e.open")
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        await page.locator(".study-adjust .study-settings").evaluate(
            "e => e.scrollTop = e.scrollHeight"
        )
        assert await page.locator("[data-study-copy]").is_visible()
        await page.keyboard.press("Escape")
        await page.mouse.move(160, 650)
        await page.mouse.wheel(0, 800)
        await page.wait_for_function("scrollY > 100")
        passed.append(
            "320px: selector, gallery selection, exclusive drawers, scrolling settings and normal page scrolling"
        )

        for width in (320, 768, 1440):
            await page.set_viewport_size({"width": width, "height": 1000})
            for theme in ("dark", "light"):
                await page.goto(
                    BASE + f"/opt/?v=contour&theme={theme}", wait_until="networkidle"
                )
                await LAYOUT_AUDIT["settle_page"](page, True)
                await page.locator(".study-browse summary").click()
                audit = await page.evaluate(
                    LAYOUT_AUDIT["AUDIT_JS"],
                    {
                        "touch": width <= 768,
                        "controlSelector": LAYOUT_AUDIT["CONTROL_SELECTOR"],
                        "javascript": True,
                    },
                )
                assert not audit["issues"], (width, theme, audit["issues"])
        passed.append(
            "open gallery: target sizes, text contrast and clipping at 320/768/1440px in both themes"
        )

        await page.goto(
            BASE + "/opt/?v=vector&grain=NaN&grid=-100&glow=999",
            wait_until="networkidle",
        )
        assert await page.locator("#study-grain").input_value() == "20"
        assert await page.locator("#study-grid").input_value() == "24"
        assert await page.locator("#study-glow").input_value() == "160"
        await page.goto(BASE + "/", wait_until="networkidle")
        assert await page.locator("html").get_attribute("data-study") is None
        assert await page.locator(".study-bar").count() == 0
        passed.append(
            "invalid URL values bounded; design choices stay isolated from normal website"
        )
        await context.close()

        blocked = await browser.new_context(viewport={"width": 390, "height": 844})
        await blocked.add_init_script(
            "Object.defineProperty(window, 'localStorage', {get(){throw new Error('blocked')}})"
        )
        page = await blocked.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(
            BASE + "/opt/?v=afterglow&grain=12&theme=light", wait_until="networkidle"
        )
        assert await page.locator("html").get_attribute("data-study") == "afterglow"
        await page.locator("[data-study-preset]").select_option("blueprint")
        assert await page.locator("html").get_attribute("data-study") == "blueprint"
        await blocked.close()
        no_js = await browser.new_context(java_script_enabled=False)
        page = await no_js.new_page()
        await page.goto(BASE + "/opt/", wait_until="networkidle")
        assert (await page.locator("h1").text_content()).strip() == "Jonas Mehtali"
        assert await page.locator(".study-noscript").is_visible()
        assert await page.locator(".study-row").is_hidden()
        passed.append(
            "storage blocked: controls work; JavaScript disabled: readable page with clear fallback"
        )
        await browser.close()
    assert not errors, errors
    print(json.dumps({"browser": ENGINE, "passed": passed, "errors": errors}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
