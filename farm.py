#!/usr/bin/env python3
"""vyce farm — camoufox solve + register + verify — SEMUA dari IP laptop (residensial).

Token turnstile IP-bound: solve browser dan API register harus keluar dari exit IP
yang sama. Camoufox render halaman signup, token dipanen dari iframe, lalu
register/tembak dilanjutkan dari proses python ini (IP sama).
"""
import asyncio, json, sys, time, os, hashlib, base64, random, string
import urllib.request, urllib.error
from camoufox.async_api import AsyncCamoufox

BASE = "https://vyceai.com"
SITEKEY = "0x4AAAAAAD5F6BfSHmTDWS4a"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vyce_accounts.jsonl")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36")


def _api(method, path, body=None, timeout=45):
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": UA, "Accept": "application/json",
         "Content-Type": "application/json", "Origin": BASE,
         "Referer": BASE + "/signup"}
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def mail_tm():
    d = json.loads(urllib.request.urlopen("https://api.mail.tm/domains", timeout=20).read())
    dom = random.choice([x["domain"] for x in d["hydra:member"] if x.get("isActive")])
    em = "vyce" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@" + dom
    pw = "Vyce!" + "".join(random.choices(string.ascii_letters + string.digits, k=12))
    b = json.dumps({"address": em, "password": pw}).encode()
    r = urllib.request.Request("https://api.mail.tm/accounts", data=b,
                               headers={"Content-Type": "application/json"})
    json.loads(urllib.request.urlopen(r, timeout=20).read())
    r = urllib.request.Request("https://api.mail.tm/token",
                               data=json.dumps({"address": em, "password": pw}).encode(),
                               headers={"Content-Type": "application/json"})
    tok = json.loads(urllib.request.urlopen(r, timeout=20).read())["token"]
    return em, pw, tok


def pow_solve(ch):
    salt = ch.get("salt") or ""
    prefix = ch["id"][:32]
    epoch = str(ch.get("epoch", ""))
    diff = int(ch["difficulty"])
    deadline = time.time() + 110
    n = 0
    while time.time() < deadline:
        for _ in range(512):
            h1 = hashlib.sha256(f"vyce-pow-v4:{salt}:{ch['prefix']}:{ch['id']}:{n}:register".encode()).digest()
            h2 = hashlib.sha256(f"vyce-auth-seal-v4:{prefix}:{h1.hex()}:{n}:{epoch}".encode()).digest()
            bits = 0
            for byte in h2:
                if byte == 0:
                    bits += 8
                    continue
                bits += 8 - byte.bit_length()
                break
            if bits >= diff:
                return n
            n += 1
    raise TimeoutError("pow")


async def solve_token(page):
    """Reload signup, dump token from hidden input once CF fills it."""
    await page.goto(BASE + "/signup", wait_until="domcontentloaded", timeout=60000)
    for _ in range(24):
        await asyncio.sleep(4)
        v = await page.evaluate(
            "() => { const i=document.querySelector('input[name=cf-turnstile-response]'); return i? i.value : ''; }")
        if v and len(v) > 50:
            return v
    return None


async def farm_one(idx, page):
    print(f"\n===== [{idx}] =====")
    em, pw, mailtok = mail_tm()
    print(f"email   : {em}")

    tok = await solve_token(page)
    if not tok:
        print("✗ no turnstile token")
        return None
    print(f"ts-token: {tok[:50]}... ({len(tok)}c)")

    st, raw = _api("GET", "/user/csrf")
    csrf = json.loads(raw)["token"]

    st, raw = _api("GET", "/user/pow?purpose=register")
    ch = json.loads(raw)
    nonce = pow_solve(ch)
    print(f"pow     : nonce={nonce} diff={ch['difficulty']}")

    body = {"email": em, "password": pw, "name": "vyce user", "captchaToken": tok,
            "csrfToken": csrf, "powId": ch["id"], "powNonce": nonce,
            "fingerprint": base64.b64encode(os.urandom(32)).decode(),
            "fpVersion": "gy5ij7wh", "machineId": os.urandom(16).hex()}
    st, raw = _api("POST", "/user/register", body)
    print(f"register: http={st} {raw[:180]}")
    if st not in (200, 201):
        return None
    acc = json.loads(raw)
    if isinstance(acc, dict):
        acc["_email"], acc["_password"], acc["_mailtok"] = em, pw, mailtok
    else:
        acc = {"_raw": acc, "_email": em, "_password": pw, "_mailtok": mailtok}
    return acc


async def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    ok = 0
    async with AsyncCamoufox(headless=True, humanize=True) as browser:
        page = await browser.new_page()
        # warm up CF session
        await page.goto(BASE + "/signup", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(6)
        for i in range(1, count + 1):
            try:
                acc = await farm_one(i, page)
                if acc:
                    with open(OUT, "a") as f:
                        f.write(json.dumps(acc) + "\n")
                    ok += 1
                    print(f"✓ SAVED ({ok}/{count})")
            except Exception as e:
                print(f"✗ ERR: {e}")
            await asyncio.sleep(4)
    print(f"\nDONE {ok}/{count}")


if __name__ == "__main__":
    asyncio.run(main())
