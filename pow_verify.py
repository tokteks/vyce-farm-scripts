#!/usr/bin/env python3
"""verify PoW purpose-arg hypothesis against live server."""
import hashlib, json, time, urllib.request, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"


def get(path):
    r = urllib.request.Request("https://vyceai.com" + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(r, timeout=25) as resp:
        return json.loads(resp.read().decode())


def leading_bits(h2: bytes) -> int:
    bits = 0
    for byte in h2:
        if byte == 0:
            bits += 8
            continue
        return bits + 8 - byte.bit_length()
    return bits


def solve(ch, purpose):
    salt = ch.get("salt") or ""
    prefix = ch["id"][:32]
    epoch = ch.get("epoch", 0)
    diff = ch["difficulty"]
    t0 = time.time()
    n = 0
    while time.time() - t0 < 60:
        for _ in range(1024):
            h1 = hashlib.sha256(f"vyce-pow-v4:{salt}:{ch['prefix']}:{ch['id']}:{n}:{purpose}".encode()).hexdigest()
            h2 = hashlib.sha256(f"vyce-auth-seal-v4:{prefix}:{h1}:{n}:{epoch}".encode()).digest()
            if leading_bits(h2) >= diff:
                return n, time.time() - t0
            n += 1
    return None, None


ch = get("/user/pow?purpose=register")
print("challenge:", json.dumps(ch))
for purpose in ("register", "auth"):
    n, el = solve(ch, purpose)
    print(f"purpose={purpose!r}: nonce={n} elapsed={el}")
    if n is not None:
        break
