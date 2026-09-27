#!/usr/bin/env python3
"""Turnstile auto-mode solver for vyceai — placeholder-based form selectors.

Pattern (reusable): turnstile 'auto' mode fills the hidden input only after a
user gesture or form submit. Steps:
1. fill form by PLACEHOLDER (vyceai form has no name attrs)
2. click submit -> CF challenge fires (checkbox/interactive iframe appears)
3. if checkbox iframe: click it
4. poll hidden input until token set
"""
import asyncio
import random
import sys

URL = "https://vyceai.com/signout"  # placeholder, overridden below
URL = "https://vyceai.com/signup"


def rnd(a, b):
    return random.randint(a, b)


async def dump_tok(page, tag):
    val = await page.evaluate(
        "() => document.querySelector('input[name=\"cf-turnstile-response\"]')?.value || ''")
    print(f"[{tag}] token={'SET:' + val[:28] + '...' if val else 'empty'}")
    return val


async def cf_click(page):
    for fr in page.frames:
        if "challenges.cloudflare.com" in (fr.url or ""):
            try:
                el = await fr.frame_element()
                box = await el.bounding_box()
                if box and box["width"] > 15:
                    await page.mouse.move(box["x"] + box["width"] / 2,
                                          box["y"] + box["height"] / 2,
                                          steps=rnd(3, 6))
                    await page.wait_for_timeout(rnd(100, 300))
                    await page.mouse.down()
                    await page.wait_for_timeout(rnd(50, 150))
                    await page.mouse.up()
                    print(f"[*] clicked cf frame {box}")
                    return True
            except Exception as e:
                print(f"[!] cf click err: {e}")
    return False


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
        await page.wait_for_timeout(3000)

        tok = await dump_tok(page, "initial")

        # fill by placeholder
        if not tok:
            print("[*] filling form (placeholder selectors)")
            email = f"vyce{random.randint(10**9,10**10-1)}@mail.tm"
            password = "Vyce!" + "".join(random.choices(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=10))
            try:
                await page.fill('input[placeholder="Jane Doe"]', "vyce probe")
                await page.fill('input[placeholder="you@example.com"]', email)
                await page.fill('input[placeholder="••••••••"]', password)
            except Exception as e:
                print(f"[!] fill err: {e}")

            print("[*] clicking Create Account (triggers auto turnstile)")
            try:
                await page.click('button:has-text("Create Account")')
            except Exception as e:
                print(f"[!] submit err: {e}")
            await page.wait_for_timeout(5000)
            tok = await dump_tok(page, "after-submit")
            await page.screenshot(path="ts_after_submit.png")

        # click checkbox if it appeared
        if not tok:
            for i in range(10):
                print(f"[*] poll {i} — trying cf click")
                clicked = await cf_click(page)
                await page.wait_for_timeout(2500)
                tok = await dump_tok(page, f"poll{i}")
                if tok:
                    break
                if i == 3:
                    # maybe error msg; reload and retry whole flow once
                    print("[*] reload retry")
                    await page.reload(wait_until="networkidle")
                    await page.wait_for_timeout(3000)

        await page.screenshot(path="ts_final.png")
        if tok:
            with open("turnstile_token.txt", "w") as f:
                f.write(tok)
            print("[*] TOKEN SAVED")
        else:
            print("[!] NO TOKEN")
        await b.close()


asyncio.run(main())
