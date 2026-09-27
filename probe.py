#!/usr/bin/env python3
"""vyce probe — register 1-5 akun via /user/register.

Chain: mail.tm email -> csrf -> pow solve -> turnstile token -> register -> login -> key.
"""
import base64
import hashlib
import json
import os
import random
import string
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

BASE = "https://vyceai.com"
SITEKEY = "0x4AAAAAAD5F6BfSHmTDWS4a"
SOLVER = os.environ.get("SOLVER_URL", "http://127.0.0.1:8888")
COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 1
OUT = os.environ.get("VYCE_OUT", "vyce_accounts.jsonl")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36")

_session = {"cookies": {}}


def _req(method, path, body=None, headers=None, origin=None, timeout=40):
    url = BASE + path if path.startswith("/") else path
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": UA, "Accept": "application/json",
         "Content-Type": "application/json", "Origin": origin or BASE,
         "Referer": BASE + "/signup"}
    for k, v in (headers or {}).items():
        h[k] = v
    if _session["cookies"]:
        h["Cookie"] = "; ".join(f"{k}={v}" for k, v in _session["cookies"].items())
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            for c in resp.headers.get_all("Set-Cookie") or []:
                kv = c.split(";")[0]
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    _session["cookies"][k] = v
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        return e.code, raw


def solve_pow(challenge):
    """SHA-256d bit-difficulty PoW — algorithm from vyceai bundle."""
    salt = challenge.get("salt") or ""
    prefix = challenge["id"][:32]
    epoch = str(challenge.get("epoch", ""))
    diff = int(challenge["difficulty"])
    deadline = time.time() + 110
    n = 0
    batch = 512
    while time.time() < deadline:
        for _ in range(batch):
            h1 = hashlib.sha256(
                f"vyce-pow-v4:{salt}:{challenge['prefix']}:{challenge['id']}:{n}:register".encode()
            ).digest()
            h2 = hashlib.sha256(
                f"vyce-auth-seal-v4:{prefix}:{h1.hex()}:{n}:{epoch}".encode()
            ).digest()
            # count leading zero bits
            bits = 0
            for byte in h2:
                if byte == 0:
                    bits += 8
                    continue
                bits += 8 - byte.bit_length()
                break
            if bits >= diff:
                return n, time.time() + 60 - (deadline - 110 - time.time())
            n += 1
    raise TimeoutError("pow not solved in budget")


def get_turnstile():
    r = urllib.request.urlopen(
        SOLVER + f"/turnstile?url={urllib.parse.quote(BASE + '/signup', safe='')}&sitekey={SITEKEY}",
        timeout=60)
    tid = json.loads(r.read().decode())["taskId"]
    for _ in range(40):
        time.sleep(5)
        r = urllib.request.urlopen(SOLVER + f"/result?id={tid}", timeout=30)
        d = json.loads(r.read().decode())
        if d.get("status") == "ready":
            return d["solution"]["token"]
        if d.get("errorId"):
            raise RuntimeError(f"solver fail: {d.get('errorCode')}")
    raise TimeoutError("turnstile timeout")


def mail_tm_account():
    d = json.loads(urllib.request.urlopen("https://api.mail.tm/domains", timeout=20).read())
    dom = random.choice([x["domain"] for x in d["hydra:member"] if x.get("isActive")])
    user = "vyce" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email = f"{user}@{dom}"
    pw = "Vyce!" + "".join(random.choices(string.ascii_letters + string.digits, k=12))
    body = json.dumps({"address": email, "password": pw}).encode()
    r = urllib.request.Request("https://api.mail.tm/accounts", data=body,
                                headers={"Content-Type": "application/json"})
    json.loads(urllib.request.urlopen(r, timeout=20).read())
    r = urllib.request.Request("https://api.mail.tm/token",
                                data=json.dumps({"address": email, "password": pw}).encode(),
                                headers={"Content-Type": "application/json"})
    tok = json.loads(urllib.request.urlopen(r, timeout=20).read())["token"]
    return email, pw, tok


def register_one(idx):
    print(f"\n=== [{idx}] mail.tm inbox ===")
    email, pw, mail_tok = mail_tm_account()
    print(f"  email: {email}")

    print("  csrf...")
    st, raw = _req("GET", "/user/csrf")
    csrf = json.loads(raw)["token"]
    print(f"  csrf ok ({csrf[:12]}...)")

    print("  pow...")
    st, raw = _req("GET", "/user/pow?purpose=register")
    ch = json.loads(raw)
    t0 = time.time()
    nonce, _ = solve_pow(ch)
    print(f"  pow solved nonce={nonce} in {time.time()-t0:.1f}s (diff={ch['difficulty']})")

    print("  turnstile...")
    tok = get_turnstile()
    print(f"  token {tok[:24]}...")

    body = {
        "email": email, "password": pw, "name": "vyce farm",
        "captchaToken": tok, "csrfToken": csrf,
        "powId": ch["id"], "powNonce": nonce,
        "fingerprint": base64.b64encode(os.urandom(32)).decode(),
        "fpVersion": "gy5ij7wh", "machineId": os.urandom(16).hex(),
    }
    print("  register...")
    st, raw = _req("POST", "/user/register", body)
    print(f"  http={st} -> {raw[:200]}")
    if st not in (200, 201):
        return None
    acc = json.loads(raw)
    acc["email"], acc["password"] = email, pw
    acc["mail_token"] = mail_tok
    return acc


if __name__ == "__main__":
    print(f"vyce probe — {COUNT} akun -> {OUT}")
    ok = 0
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), OUT), "a") as f:
        for i in range(1, COUNT + 1):
            try:
                a = register_one(i)
                if a:
                    f.write(json.dumps(a) + "\n")
                    f.flush()
                    ok += 1
                    print(f"  ✓ SAVED (total ok={ok})")
            except Exception as e:
                print(f"  ✗ ERROR: {e}")
            time.sleep(3)
    print(f"\nDONE: {ok}/{COUNT}")
