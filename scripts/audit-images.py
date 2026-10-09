#!/usr/bin/env python3
"""Exercise image-study choices, votes, motion and image-loading failure paths."""

import asyncio
import json
import sys
from pathlib import Path
from runpy import run_path
from urllib.parse import parse_qs, urlsplit

from playwright.async_api import async_playwright


BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8776").rstrip("/")
ENGINE = sys.argv[2] if len(sys.argv) > 2 else "chromium"
ROOT = Path(__file__).resolve().parents[1]
DETAILS = json.loads((ROOT / "design-lab/retrofuturism/details.json").read_text())
LAYOUT = run_path(str(Path(__file__).with_name("audit-site.py")))
HERO = ".hub-hero__photo"


async def explore(page, pane):
    if not await page.locator(".study-browse").evaluate("e => e.open"):
        await page.locator(".study-browse summary").click()
    await page.locator(f'[data-study-pane="{pane}"]').click()


async def finish_motion(page):
    # Chromium can retain unresolved finished promises for button transitions
    # removed with a closed <details>. Observe image cleanup itself instead.
    await page.wait_for_function(
        "!document.querySelector('[data-image-playing]')", timeout=2500
    )


async def photo_pixels(page):
    # Exclude the rounded outer edge, whose antialiasing can differ by one RGB
    # level after Chromium removes a compositing layer. Compare the photograph.
    box = await page.locator(HERO + " img").bounding_box()
    return await page.screenshot(
        clip={
            "x": box["x"] + 8,
            "y": box["y"] + 8,
            "width": box["width"] - 16,
            "height": box["height"] - 16,
        }
    )


async def main():
    passed, errors = [], []
    async with async_playwright() as p:
        browser = await getattr(p, ENGINE).launch()
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1050}, reduced_motion="reduce"
        )
        await context.add_init_script("localStorage.setItem('jm.telemetry', 'off')")
        page = await context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(BASE + "/opt/?mix=relay&theme=dark")
        for key, mix in DETAILS["mixes"].items():
            await explore(page, "mixes")
            await page.locator(f'[data-mix="{key}"]').focus()
            await page.keyboard.press("Enter")
            query = parse_qs(urlsplit(page.url).query)
            for setting in ("frame", "reveal", "grain", "grid", "glow"):
                assert query[setting] == [str(mix[setting])], (key, query)
            assert query["v"] == [mix["version"]]
            assert (
                await page.locator(HERO).get_attribute("data-image-frame")
                == mix["frame"]
            )
        for key in DETAILS["frames"]:
            await explore(page, "frames")
            await page.locator(f'[data-frame="{key}"]').click()
            assert await page.locator(HERO).get_attribute("data-image-frame") == key
        for key in DETAILS["reveals"]:
            await explore(page, "reveals")
            await page.locator(f'[data-reveal="{key}"]').click()
            assert await page.locator("html").get_attribute("data-study-reveal") == key
            assert await page.locator("main [data-image-playing]").count() == 0
        await page.locator("[data-study-replay]").click()
        assert (
            "display preferences"
            in await page.locator(".study-replay-status").text_content()
        )
        assert await page.locator("[data-study-replay]").evaluate(
            "e => e === document.activeElement"
        )
        passed.append(
            "six combinations, five frames, five reveals: keyboard selection, shared settings and reduced motion"
        )

        # Record independent votes, exact mixes and notes, then recover them after navigation.
        await page.goto(BASE + "/opt/?mix=relay&theme=dark", wait_until="networkidle")
        await page.locator("[data-study-open-votes]").click()
        for group, rating in (
            ("backgrounds", "love"),
            ("frames", "love"),
            ("reveals", "maybe"),
        ):
            await page.locator(
                f'[data-vote-group="{group}"] [data-rating="{rating}"]'
            ).click()
        await page.locator("#study-vote-note").fill(
            "Keep Ion; try quieter light rails."
        )
        await page.locator("[data-save-mix]").click()
        saved_url = await page.locator("[data-saved-mix]").get_attribute("href")
        await page.locator("[data-save-mix]").click()
        assert await page.locator("[data-saved-mix]").count() == 1
        assert (
            "already saved" in await page.locator(".study-vote-status").text_content()
        )
        await page.keyboard.press("Escape")
        await (
            page.get_by_role("navigation", name="Main navigation")
            .get_by_role("link", name="Professional", exact=True)
            .click()
        )
        await page.wait_for_url("**/opt/pro/**")
        assert parse_qs(urlsplit(page.url).query)["frame"] == ["rails"]
        await page.locator("[data-study-open-votes]").click()
        assert (
            await page.locator("#study-vote-note").input_value()
            == "Keep Ion; try quieter light rails."
        )
        assert (
            await page.locator(
                '[data-vote-group="backgrounds"] [data-rating="love"]'
            ).get_attribute("aria-pressed")
            == "true"
        )
        await page.locator("[data-study-theme]").click()
        await page.wait_for_function(
            "document.querySelector('#study-vote-export').value.includes('theme=light')"
        )
        assert await page.locator("[data-saved-mix]").get_attribute("href") == saved_url
        await page.evaluate(
            "Object.defineProperty(navigator, 'clipboard', {configurable:true,value:{writeText:async t => window.copiedVotes=t}})"
        )
        await page.locator("[data-copy-votes]").click()
        copied = await page.evaluate("window.copiedVotes")
        assert (
            "Ion: love" in copied
            and "Light rails: love" in copied
            and "Light sweep: maybe" in copied
        )
        assert saved_url in copied and "Keep Ion; try quieter light rails." in copied
        # HTTP fallback must copy the whole ballot, keep the drawer open and restore focus.
        await page.evaluate(
            "() => { navigator.clipboard.writeText=()=>Promise.reject(new Error('denied'));document.execCommand=()=>{window.copiedFallback=document.querySelector('.study-copy-buffer').value;return true}; }"
        )
        await page.locator("[data-copy-votes]").click()
        assert await page.evaluate("window.copiedFallback") == copied
        assert await page.locator("[data-copy-votes]").evaluate(
            "e=>e===document.activeElement"
        )
        await page.evaluate("document.execCommand=()=>false")
        await page.locator("[data-copy-votes]").click()
        assert await page.locator("#study-vote-export").evaluate(
            "e=>e===document.activeElement && e.selectionEnd===e.value.length"
        )
        await page.locator("[data-saved-mix]").click()
        await page.wait_for_url(saved_url)
        assert await page.locator("html").get_attribute("data-theme") == "dark"
        await page.locator("[data-study-open-votes]").click()
        await page.locator('[data-vote-group="reveals"] [data-rating="maybe"]').click()
        assert (
            await page.locator(
                '[data-vote-group="reveals"] [aria-pressed="true"]'
            ).count()
            == 0
        )
        await page.locator(".study-saved-mixes button").click()
        assert await page.locator("[data-saved-mix]").count() == 0
        passed.append(
            "votes, notes and exact saved mixes persist; clipboard success, HTTP fallback and denial recovery; clear/remove controls"
        )

        # All five drawer panels must fit real phone, tablet and desktop layouts.
        for width in (320, 768, 1440):
            await page.set_viewport_size({"width": width, "height": 1000})
            for theme in ("dark", "light"):
                await page.goto(BASE + f"/opt/?mix=aperture&theme={theme}")
                await LAYOUT["settle_page"](page, True)
                for pane in ("mixes", "backgrounds", "frames", "reveals", "votes"):
                    await explore(page, pane)
                    await page.evaluate("document.fonts.ready")
                    audit = await page.evaluate(
                        LAYOUT["AUDIT_JS"],
                        {
                            "touch": width <= 768,
                            "controlSelector": LAYOUT["CONTROL_SELECTOR"],
                            "javascript": True,
                        },
                    )
                    assert not audit["issues"], (width, theme, pane, audit["issues"])
        passed.append(
            "30 open-panel layouts: text contrast, clipping, control sizes and ornaments in both themes at 320/768/1440px"
        )
        await context.close()

        # Test real motion separately from the reduced-motion layout audit.
        motion = await browser.new_context(viewport={"width": 1440, "height": 1050})
        await motion.add_init_script("localStorage.setItem('jm.telemetry','off')")
        page = await motion.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(BASE + "/opt/?mix=relay&theme=dark", wait_until="networkidle")
        await finish_motion(page)
        for key in DETAILS["reveals"]:
            await explore(page, "reveals")
            await page.locator(f'[data-reveal="{key}"]').click()
            await finish_motion(page)
            before = await page.locator(HERO).bounding_box()
            clean = await photo_pixels(page)
            await page.locator("[data-study-replay]").click()
            if key != "still":
                await page.wait_for_selector(f'{HERO}[data-image-playing="{key}"]')
                await page.evaluate(
                    "document.querySelectorAll('main [data-image-playing]').forEach(e=>e.getAnimations({subtree:true}).forEach(a=>{a.pause();a.currentTime=a.effect.getTiming().duration/2}))"
                )
                moving = await photo_pixels(page)
                assert clean != moving, (key, "effect did not change image pixels")
                await page.evaluate("document.getAnimations().forEach(a=>a.finish())")
                await finish_motion(page)
            assert await page.locator(HERO).bounding_box() == before
            assert clean == await photo_pixels(page), (
                key,
                "image did not return to its clean rendering",
            )
            assert (
                await page.locator(
                    "main [data-image-playing], main .study-load-sweep"
                ).count()
                == 0
            )
            assert await page.locator(HERO + " img").evaluate(
                "e => { const s=getComputedStyle(e); return s.clipPath==='none' && s.filter==='none' && s.opacity==='1' && !e.getAnimations().length; }"
            )
        await page.locator("[data-study-replay]").click()
        await page.emulate_media(reduced_motion="reduce")
        await page.wait_for_function(
            "!document.querySelector('main [data-image-playing]')"
        )
        assert await page.locator(HERO + " img").evaluate(
            "e=>getComputedStyle(e).clipPath==='none'"
        )
        await page.emulate_media(reduced_motion="no-preference")
        await page.reload(wait_until="networkidle")
        await finish_motion(page)
        assert await page.locator(HERO).get_attribute("data-image-load") == "ready"
        passed.append(
            "all entrances change pixels, reserve layout and settle to the original image; replay, cached reload and live reduced-motion cancellation"
        )

        # Gate the actual hero response to prove effects never conceal a slow or failed image.
        src = await page.locator(HERO + " img").get_attribute("src")
        gate = asyncio.Event()

        async def delay(route):
            await gate.wait()
            await route.continue_()

        await page.route("**" + src, delay)
        await page.goto(BASE + "/opt/?mix=relay", wait_until="domcontentloaded")
        await page.wait_for_selector(HERO + '[data-image-load="waiting"]')
        assert await page.locator(HERO + " img").evaluate(
            "e=>getComputedStyle(e).opacity==='1'"
        )
        gate.set()
        await page.wait_for_selector(HERO + '[data-image-load="ready"]')
        await finish_motion(page)
        await page.unroute("**" + src, delay)
        await page.route("**" + src, lambda route: route.abort())
        await page.reload(wait_until="networkidle")
        assert await page.locator(HERO).get_attribute("data-image-load") == "error"
        assert await page.locator(HERO).get_attribute("data-image-playing") is None
        assert await page.locator(HERO + " img").get_attribute("alt")
        await page.locator("[data-study-replay]").click()
        assert await page.locator(HERO + " img").evaluate(
            "e=>getComputedStyle(e).clipPath==='none'"
        )
        passed.append(
            "slow and failed image responses retain reserved space and accessible fallback; no stuck mask or loading animation"
        )
        await motion.close()

        blocked = await browser.new_context()
        await blocked.add_init_script(
            "Object.defineProperty(window,'localStorage',{get(){throw new Error('blocked')}})"
        )
        page = await blocked.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(BASE + "/opt/?mix=ghost&frame=invalid&reveal=invalid")
        assert await page.locator("html").get_attribute("data-study-frame") == "corners"
        assert await page.locator("html").get_attribute("data-study-reveal") == "still"
        await page.locator("[data-study-open-votes]").click()
        await page.locator(
            '[data-vote-group="backgrounds"] [data-rating="love"]'
        ).click()
        assert (
            "storage is unavailable"
            in await page.locator(".study-vote-status").text_content()
        )
        assert "Ion: love" in await page.locator("#study-vote-export").input_value()
        passed.append(
            "invalid options fall back safely; blocked storage still allows voting and text export"
        )
        await browser.close()
    assert not errors, errors
    print(json.dumps({"browser": ENGINE, "passed": passed, "errors": errors}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
