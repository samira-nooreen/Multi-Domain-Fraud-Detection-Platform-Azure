import os
from pathlib import Path

root = Path('.')
files = []
for p in root.rglob('*'):
    if p.is_file():
        try:
            files.append((p.stat().st_size, str(p)))
        except Exception:
            pass
files.sort(reverse=True)
for size, path in files[:80]:
    print(f"{size/1024:.2f} KB\t{path}")
