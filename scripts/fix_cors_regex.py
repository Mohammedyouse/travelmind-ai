"""Fix the CORS allow_origin_regex in app.py — run from project root."""
import re, sys, pathlib

path = pathlib.Path("backend/app/api/app.py")
text = path.read_text(encoding="utf-8")

# Find the exact bytes that live in the file for allow_origin_regex
idx = text.find("allow_origin_regex=")
if idx == -1:
    print("ERROR: allow_origin_regex not found", file=sys.stderr)
    sys.exit(1)

end = text.index("\n", idx)
old_line = text[idx:end]
print("OLD:", repr(old_line))

# Replace with the correct raw regex
new_line = r'        allow_origin_regex=r"^https://.*\.(?:netlify\.app|vercel\.app|onrender\.com)$",'
print("NEW:", repr(new_line))

new_text = text[:idx] + new_line + text[end:]
path.write_text(new_text, encoding="utf-8")
print("Done — CORS regex fixed.")
