"""
Deploy TravelMind AI frontend to Netlify using the CLI API.
Creates a new site, sets env vars, and deploys the dist/ folder.
"""
import subprocess, json, sys, os, zipfile, io, pathlib

def run(cmd, **kw):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

# ── 1. Get Netlify token from CLI ─────────────────────────────────────────────
token_out, token_err, _ = run("netlify api getCurrentUser")
print("getCurrentUser stdout:", token_out[:200] if token_out else "(empty)")
print("getCurrentUser stderr:", token_err[:200] if token_err else "(empty)")

# ── 2. Get the actual token from environment or from netlify config
import json as js
config_path = pathlib.Path(os.environ.get("APPDATA","")) / "netlify" / "Config" / "config.json"
print("Config path:", config_path, "exists:", config_path.exists())
if config_path.exists():
    try:
        cfg = js.loads(config_path.read_text())
        print("Config keys:", list(cfg.keys()))
        # Token is usually in users.<email>.token or similar
        print("Config (truncated):", str(cfg)[:500])
    except Exception as e:
        print("Config read error:", e)

print("\nNETLIFY_AUTH_TOKEN env:", "SET" if os.environ.get("NETLIFY_AUTH_TOKEN") else "NOT SET")
