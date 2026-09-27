#!/usr/bin/env python3
"""Dump real form DOM + CF frame content to understand widget state."""
import asyncio

URL = "https://vyceai.com/signup"


async def main():
    from patchright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await b.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)

        inputs = await page.eval_on_selector_all(
            "input, button", """els => els.map(e => ({
                tag: e.tagName, type: e.type, name: e.name, id: e.id,
                ph: e.placeholder, txt: (e.innerText||'').slice(0,30)
            }))""")
        print("=== INPUTS/BUTTONS ===")
        for i in inputs:
            print(f"  {i['tag']:<6} type={i['type'] or '-':<10} name={i['name'] or '-':<18} "
                  f"id={i['id'] or '-':<18} ph={i['ph'] or '-'} {i['txt']}")

        print("\n=== CF FRAME CONTENT ===")
        for f in page.frames:
            if "challenges.cloudflare.com" in (f.url or ""):
                print(f"frame: {f.url[:100]}")
                try:
                    content = await f.content()
                    print(f"  len={len(content)}")
                    print(f"  text={content[:600]!r}")
                except Exception as e:
                    print(f"  content err: {e}")

        # check for cf-turnstile div attrs
        ts = await page.evaluate("""() => {
            const els = [...document.querySelectorAll('[class*=turnstile],[data-sitekey],.cf-turnstile')];
            return els.map(e => ({cls: e.className, sk: e.getAttribute('data-sitekey'),
                                  action: e.getAttribute('data-action'), theme: e.getAttribute('data-theme')}));
        }""")
        print("\n=== TURNSTILE DIVS ===")
        for t in ts:
            print(f"  {t}")
        await page.screenshot(path="ts_dom.png")
        await b.close()


asyncio.run(main())
