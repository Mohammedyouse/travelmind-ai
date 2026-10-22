"""Verify CORS regex matches the expected domains."""
import re, pathlib

text = pathlib.Path("backend/app/api/app.py").read_text(encoding="utf-8")
idx = text.find("allow_origin_regex=")
end = text.index("\n", idx)
line = text[idx:end]
print("Line in file:", repr(line))

# Extract the pattern string from the line
m = re.search(r'allow_origin_regex=r"([^"]+)"', line)
if not m:
    print("COULD NOT EXTRACT PATTERN")
else:
    pattern = m.group(1)
    print("Pattern:", repr(pattern))
    test_cases = [
        ("https://travelmind-ai.netlify.app", True),
        ("https://travelmind.vercel.app",     True),
        ("https://travelmind-api.onrender.com", True),
        ("http://travelmind.netlify.app",     False),
        ("https://evil.com",                  False),
        ("http://localhost:5173",             False),
    ]
    all_ok = True
    for url, expected in test_cases:
        result = bool(re.match(pattern, url))
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}]  {url!r} -> {result} (expected {expected})")
        if result != expected:
            all_ok = False
    print("ALL PASS" if all_ok else "SOME FAILURES")
