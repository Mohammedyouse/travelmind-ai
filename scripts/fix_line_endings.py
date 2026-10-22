"""Ensure backend/start.sh has Unix LF line endings (required for Render Linux containers)."""
import pathlib
p = pathlib.Path("backend/start.sh")
content = p.read_bytes()
lf = content.replace(b"\r\n", b"\n")
p.write_bytes(lf)
print(f"Done — {len(lf)} bytes, LF endings confirmed")
