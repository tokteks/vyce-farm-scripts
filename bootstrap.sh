#!/bin/bash
# vyce-farm bootstrap — paste this into the VPS console (or wget from raw github after push)
set -e
export DEBIAN_FRONTEND=noninteractive

echo "[1/6] apt update"
apt-get update -qq

echo "[2/6] install packages"
apt-get install -y -qq python3 python3-venv python3-pip curl jq git ca-certificates > /dev/null

echo "[3/6] venv + curl_cffi"
python3 -m venv /opt/vyceenv
/opt/vyceenv/bin/pip install -q --upgrade pip
/opt/vyceenv/bin/pip install -q curl_cffi requests

echo "[4/6] workspace"
mkdir -p /opt/vyce-farm/output

echo "[5/6] probe vyce endpoints from this VPS"
cat > /opt/vyce-farm/probe.py <<'EOF'
import time
from curl_cffi import requests as cr

s = cr.Session(impersonate="chrome124")
try:
    ip = s.get("https://api.ipify.org", timeout=10).text
except Exception:
    ip = "?"
print("EXIT_IP:", ip)

for name, url in [
    ("csrf",       "https://vyceai.com/user/csrf"),
    ("pow",        "https://vyceai.com/user/pow?purpose=register"),
    ("root",       "https://vyceai.com/"),
    ("signup",     "https://vyceai.com/signup"),
    ("v1models",   "https://vyceai.com/v1/models"),
    ("health",     "https://vyceai.com/health"),
]:
    t0 = time.time()
    try:
        r = s.get(url, timeout=25)
        ms = int((time.time() - t0) * 1000)
        fg = ("Fortinet" in r.text) or ("Web Page Blocked" in r.text)
        hdr = {}
        for h in ("content-type", "server", "cf-ray"):
            hdr[h] = r.headers.get(h)
        print(f"{name:10s} code={r.status_code} len={len(r.text):6d} {ms:5d}ms fg={fg} hdr={hdr}")
        print("           body:", r.text[:160].replace("\n", " "))
    except Exception as e:
        print(f"{name:10s} ERR {type(e).__name__} {str(e)[:80]}")
EOF
/opt/vyceenv/bin/python3 /opt/vyce-farm/probe.py

echo "[6/6] done"
