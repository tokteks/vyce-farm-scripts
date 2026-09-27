#!/usr/bin/env python3
"""Camoufox turnstile solve — vyceai sitekey. Firefox anti-detect, local IP residensial."""
import asyncio, json, sys, time, os
from camoufox.async_api import AsyncCamoufox

SITEKEY = "0x4AAAAAAD5F6BfSHmTDWS4a"
TARGET = "https://vyceai.com/signup"


async def main():
    async with AsyncCamoufox(headless=True, humanize=True) as browser:
        page = await browser.new_page()
        tokens = []

        async def on_console(msg):
            pass

        # intercept the token where CF writes it
        await page.add_init_script("""
            window.__ts_tokens = [];
            const obs = new MutationObserver(() => {
                document.querySelectorAll('input[name=cf-turnstile-response]').forEach(i => {
                    if (i.value && !window.__ts_tokens.includes(i.value)) {
                        window.__ts_tokens.push(i.value);
                    }
                });
            });
            document.addEventListener('DOMContentLoaded', () => {
                obs.observe(document.body, {childList: true, subtree: true});
            });
        """)
        await page.goto(TARGET, wait_until="domcontentloaded", timeout=60000)
        print("loaded, waiting for widget...")
        for i in range(24):
            await asyncio.sleep(5)
            try:
                toks = await page.evaluate("() => (window.__ts_tokens||[]).slice()")
                if toks and len(toks[-1]) > 50:
                    print(f"TOKEN[{len(toks[-1])}]: {toks[-1][:80]}...")
                    with open("vyce_ts_token.txt", "w") as f:
                        f.write(toks[-1])
                    print("saved vyce_ts_token.txt")
                    return True
                # also check direct input value
                v = await page.evaluate("() => { const i=document.querySelector('input[name=cf-turnstile-response]'); return i ? i.value : ''; }")
                if v and len(v) > 50:
                    print(f"TOKEN via input[{len(v)}]: {v[:80]}...")
                    with open("vyce_ts_token.txt", "w") as f:
                        f.write(v)
                    print("saved vyce_ts_token.txt")
                    return True
                n = await page.evaluate("() => document.querySelectorAll('iframe').length")
                print(f"[{i}] iframes={n} waiting...")
            except Exception as e:
                print(f"[{i}] err {e}")
        await page.screenshot(path="camoufox_fail.png")
        print("FAIL - screenshot camoufox_fail.png")
        return False


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
