#!/usr/bin/env python3
"""Deep turnstile debug — a11y tree inside CF frame + JS-level interactions."""
import asyncio

URL = "https://vyceai.com/signup"


async def main():
    from patchright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        ctx = await b.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}, locale="en-US")
        page = await ctx.new_page()
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)

        # a11y snapshot of CF frame
        for fr in page.frames:
            if "challenges.cloudflare.com" in (fr.url or ""):
                print("=== CF FRAME A11Y ===")
                snap = await fr.accessibility.snapshot()
                import json as _j
                print(_j.dumps(snap, indent=1)[:1500])
                # inputs inside frame
                try:
                    els = await fr.query_selector_all("input,label,div[role=checkbox]")
                    for e in els:
                        t = await e.inner_text() if await e.is_visible() else ""
                        vis = await e.is_visible()
                        print(f"  el tag visible={vis} text={t[:60]!r}")
                except Exception as ex:
                    print(f"  sel err: {ex}")

        # try clicking the actual checkbox via frame JS
        print("\n=== JS CLICK in frame ===")
        for fr in page.frames:
            if "challenges.cloudflare.com" not in (fr.url or ""):
                continue
            for sel in ['input[type="checkbox"]', 'label', '#challenge-stage',
                        'div[role="checkbox"]', 'body']:
                try:
                    n = await fr.evaluate(f"""() => {{
                        const el = document.querySelector({sel!r});
                        if (!el) return 'missing';
                        const r = el.getBoundingClientRect();
                        if (r.width < 5) return 'tiny';
                        el.click();
                        return 'clicked ' + Math.round(r.width) + 'x' + Math.round(r.height);
                    }}""")
                    print(f"  {sel}: {n}")
                except Exception as e:
                    print(f"  {sel}: ERR {str(e)[:80]}")
        await page.wait_for_timeout(6000)
        tok = await page.evaluate(
            "() => document.querySelector('input[name=\"cf-turnstile-response\"]')?.value || ''")
        print(f"\n[*] token: {'SET' if tok else 'EMPTY'}")
        await b.close()


asyncio.run(main())
