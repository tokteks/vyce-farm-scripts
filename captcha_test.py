#!/usr/bin/env python3
"""uji register vyce: apakah captchaToken dummy bisa lolos? + escalation turnstile real."""
import json, os, sys, time, hashlib, base64, random, string, urllib.request, urllib.error, urllib.parse

BASE = "https://vyceai.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36")
_cookies = {}


def req(method, path, body=None, timeout=40):
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": UA, "Accept": "application/json",
         "Content-Type": "application/json", "Origin": BASE,
         "Referer": BASE + "/signup"}
    if _cookies:
        h["Cookie"] = "; ".join(f"{k}={v}" for k, v in _cookies.items())
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            for c in resp.headers.get_all("Set-Cookie") or []:
                kv = c.split(";")[0]
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    _cookies[k] = v
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
    raise TimeoutError


def test_register(captcha_kind):
    em, pw, mailtok = mail_tm()
    print(f"email={em}")

    st, raw = req("GET", "/user/csrf")
    csrf = json.loads(raw)["token"]
    print(f"csrf={csrf[:12]}...")

    st, raw = req("GET", "/user/pow?purpose=register")
    ch = json.loads(raw)
    nonce = pow_solve(ch)
    print(f"pow nonce={nonce} diff={ch['difficulty']}")

    if captcha_kind == "dummy":
        tok = "XXXX.DUMMY." + os.urandom(8).hex().upper()
    elif captcha_kind == "empty":
        tok = ""
    elif captcha_kind == "static":
        # token statis yang dikumpulkan dari interaksi browser manual
        tok = os.environ.get("VYCE_TS_TOKEN", "")

    body = {"email": em, "password": pw, "name": "vyce user", "captchaToken": tok,
            "csrfToken": csrf, "powId": ch["id"], "powNonce": nonce,
            "fingerprint": base64.b64encode(os.urandom(32)).decode(),
            "fpVersion": "gy5ij7wh", "machineId": os.urandom(16).hex()}
    st, raw = req("POST", "/user/register", body)
    print(f">>> http={st}")
    print(f">>> {raw[:400]}")
    if st in (200, 201):
        d = json.loads(raw)
        acc = d if isinstance(d, dict) else {}
        acc["_email"], acc["_password"], acc["_mailtok"] = em, pw, mailtok
        with open("vyce_captcha_test.json", "w") as f:
            json.dump(acc, f)
        print(">>> SAVED vyce_captcha_test.json")
    return st, raw


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "dummy"
    test_register(kind)
