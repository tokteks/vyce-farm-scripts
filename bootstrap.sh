#!/bin/bash
# vyce-farm bootstrap v2 — full stack: python env + turnstile solver + probe
# Init script pas deploy: https://raw.githubusercontent.com/tokteks/vyce-farm-scripts/main/bootstrap.sh
set -e
export DEBIAN_FRONTEND=noninteractive

echo "[1/8] apt update"
apt-get update -qq

echo "[2/8] install packages"
apt-get install -y -qq python3 python3-venv python3-pip curl jq git ca-certificates > /dev/null

echo "[3/8] venv + curl_cffi"
python3 -m venv /opt/vyceenv
/opt/vyceenv/bin/pip install -q --upgrade pip
/opt/vyceenv/bin/pip install -q curl_cffi requests

echo "[4/8] workspace"
mkdir -p /opt/vyce-farm/output

echo "[5/8] probe vyce endpoints from this VPS"
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

echo "[6/8] solver deps (quart + patchright + chromium)"
python3 -m venv /opt/solverenv
/opt/solverenv/bin/pip install -q --upgrade pip
/opt/solverenv/bin/pip install -q quart patchright rich psutil
/opt/solverenv/bin/patchright install chromium --with-deps > /dev/null 2>&1
/opt/solverenv/bin/patchright install-deps chromium > /dev/null 2>&1 || true

echo "[7/8] turnstile solver service"
mkdir -p /opt/farm/d3vin
if [ ! -f /opt/farm/d3vin/api.py ]; then
  curl -fsSL https://codeload.github.com/tokteks/vyce-farm-scripts/tar.gz/refs/heads/main | tar xz --strip-components=1 -C /tmp/vfsrc
  mv /tmp/vfsrc/d3vin/* /opt/farm/d3vin/
fi
cat > /etc/systemd/system/turnstile-solver.service <<'UNIT'
[Unit]
Description=Turnstile Solver API (vyce-farm)
After=network.target

[Service]
WorkingDirectory=/opt/farm/d3vin
ExecStart=/opt/solverenv/bin/python api.py --host 127.0.0.1 --port 8888
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now turnstile-solver
sleep 4
echo "solver: $(systemctl is-active turnstile-solver)"
curl -s -o /dev/null -w "solver_local=%{http_code}\n" http://127.0.0.1:8888/ || true

echo "[8/8] bootstrap done"
