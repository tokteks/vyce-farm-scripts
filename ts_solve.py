#!/usr/bin/env python3
"""Turnstile auto-mode solver — interact until cf-turnstile-response fills.

d3vin route-intercept fails because vyceai uses turnstile in 'auto' mode:
widget loads invisible, challenge only fires on user gesture / form submit.
This script: load page -> find widget -> click -> if empty, submit empty form ->
poll token. Reusable pattern for any auto/interactive turnstile site.
"""
import asyncio

SITEKEY = "0x4AAAAAAD5F6BfSHmTDWS4a"
URL = "https://vyceai.com/signup"


async def dump_token(page, tag):
    val = await page.eval_on_selector(
        'input[name="cf-turnstile-response"]', "el => el.value || ''")
    has = bool(val)
    print(f"[{tag}] token={'SET ' + val[:32] + '...' if has else 'empty'}")
    return val


async def main():
    from patchright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        ctx = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900}, locale="en-US")
        page = await ctx.new_page()
        await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(4000)

        # 1) click the widget iframe center (checkbox mode)
        cf_frames = [f for f in page.frames if "challenges.cloudflare.com" in (f.url or "")]
        print(f"[*] cf frames: {len(cf_frames)}")
        for fr in cf_frames:
            try:
                el = await fr.frame_element()
                box = await el.bounding_box()
                if box:
                    print(f"[*] click iframe at {box}")
                    await page.mouse.move(box["x"] + 30, box["y"] + box["height"] / 2)
                    await page.wait_for_timeout(rnd(80, 200))
                    await page.mouse.down()
                    await page.wait_for_timeout(rnd(40, 120))
                    await page.mouse.up()
                    break
            except Exception as e:
                print(f"[!] click frame err: {e}")
        await page.wait_for_timeout(3000)
        tok = await dump_token(page, "after-click")

        # 2) fill + submit empty-ish form to trigger challenge (auto mode)
        if not tok:
            print("[*] triggering via form submit")
            try:
                await page.fill('input[name="name"], #name', "vyce probe")
                await page.fill('input[name="email"], input[type="email"]', "probe@example.com")
                await page.fill('input[name="password"], input[type="password"]', "Vyce123456")
                btn = await page.query_selector('button[type="submit"], button:has-text("Create Account")')
                if btn:
                    await btn.click()
            except Exception as e:
                print(f"[!] form err: {e}")
            await page.wait_for_timeout(4000)
            tok = await dump_token(page, "after-submit")

        # 3) poll
        for i in range(12):
            if tok:
                break
            await page.wait_for_timeout(2500)
            tok = await dump_token(page, f"poll{i}")
            if not tok and cf_frames:
                # re-click widget (challenge may spawn new iframe)
                try:
                    el = await cf_frames[0].frame_element()
                    box = await el.bounding_box()
                    if box:
                        await page.mouse.click(box["x"] + 30, box["y"] + box["height"] / 2)
                except Exception:
                    pass

        await page.screenshot(path="ts_solve.png")
        if tok:
            with open("turnstile_token.txt", "w") as f:
                f.write(tok)
            print("[*] TOKEN SAVED to turnstile_token.txt")
        else:
            print("[!] FAILED — no token")
        await browser.close()


def rnd(a, b):
    import random
    return random.randint(a, b)


asyncio.run(main())
