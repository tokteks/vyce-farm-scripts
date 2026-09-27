#!/usr/bin/env python3
"""vyce akun — claim daily reward + create api key + test inference. Pakai token session."""
import json, sys, time, urllib.request, urllib.error

BASE = "https://vyceai.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36")


def api(method, path, body=None, token=None, timeout=45):
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": UA, "Accept": "application/json",
         "Content-Type": "application/json", "Origin": BASE,
         "Referer": BASE + "/dashboard"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        return 0, str(e)


accs = [json.loads(l) for l in open("vyce_accounts.jsonl", encoding="utf-8") if l.strip()]
print(f"akun terdaftar: {len(accs)}")
for i, a in enumerate(accs, 1):
    tok = a.get("token")
    print(f"\n===== [{i}] {a['_email']} bal={a['user']['totalBalance']} =====")

    st, d = api("POST", "/user/daily-reward/claim", {}, tok)
    print(f"  daily-claim: http={st} {str(d)[:150]}")

    st, d = api("GET", "/user/balance", None, tok)
    print(f"  balance    : http={st} {str(d)[:120]}")

    st, d = api("GET", "/user/referral", None, tok)
    print(f"  referral   : http={st} {str(d)[:120]}")

    st, d = api("POST", "/user/keys", {"name": "farm-key-1"}, tok)
    print(f"  create-key : http={st} {str(d)[:200]}")
    if st in (200, 201) and isinstance(d, dict):
        key = d.get("key") or d.get("apiKey") or (d.get("key", {}) or {}).get("key")
        if key:
            print(f"  🔑 API KEY : {key}")
            a["api_key"] = key
            with open("vyce_accounts.jsonl", "w", encoding="utf-8") as f:
                for x in accs:
                    f.write(json.dumps(x) + "\n")
        else:
            print("  (key field?):", list(d.keys()))
            st2, d2 = api("GET", "/user/keys", None, tok)
            print(f"  list-keys  : http={st2} {str(d2)[:250]}")
