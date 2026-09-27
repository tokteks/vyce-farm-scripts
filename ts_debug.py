#!/usr/bin/env python3
"""Debug turnstile vyce — load real signup page, screenshot, dump widget state."""
import asyncio
import sys

SITEKEY = "0x4AAAAAAD5F6BfSHmTDWS4a"
URL = "https://vyceai.com/signup"


async def main():
    from patchright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = await ctx.new_page()
        print(f"[*] goto {URL}")
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"goto err: {e}")
        await page.wait_for_timeout(6000)

        # find turnstile iframe
        frames = [f for f in page.frames if "challenges.cloudflare.com" in (f.url or "")]
        print(f"[*] cloudflare frames: {len(frames)}")
        for f in frames:
            print(f"    frame url: {f.url[:120]}")

        # hidden input state
        for sel in ['input[name="cf-turnstile-response"]', 'input[name*="turnstile"]',
                    '[class*="cf-turnstile"]', 'div[data-sitekey]']:
            try:
                els = await page.query_selector_all(sel)
                if els:
                    print(f"[*] sel {sel}: {len(els)} element(s)")
                    val = await els[0].get_attribute("value")
                    print(f"    value: {(val or '')[:60]}")
            except Exception as e:
                print(f"    {sel}: err {e}")

        # page content hints
        body = await page.inner_text("body")
        print(f"[*] body text ({len(body)} chars): {body[:300]!r}")

        await page.screenshot(path=str(sys.argv[1] if len(sys.argv) > 1 else "vyce_signup.png"),
                              full_page=False)
        print("[*] screenshot saved")
        await browser.close()


asyncio.run(main())
