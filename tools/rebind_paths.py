import io
import os
import sys

OLD = r"<AiQQ>"
NEW = ""

if len(sys.argv) >= 3:
    OLD, NEW = sys.argv[1], sys.argv[2].rstrip("\\/")

if not OLD or not NEW:
    print("usage: python rebind_paths.py <old-root> <new-root>")
    sys.exit(1)

# \u53ea\u6539\u914d\u7f6e/\u811a\u672c/\u8865\u4e01\uff0c\u4e0d\u6539\u5386\u53f2\u8bb0\u5f55\u4e0e\u65e5\u5fd7
targets = [
    r"tools\qzone_web.py",
    r"tools\napcat_qr_watch.py",
    r"tools\restart_napcat.ps1",
    r"tools\pack_transfer.ps1",
    r"start_cortico.bat",
    r"stop_cortico.bat",
    r"Cortico\deployments\mybot\config.json",
    r"Cortico\deployments\mybot\shuoming.txt",
    r"Cortico\extensions\node_modules\.pnpm\cortico-world-qq-final@0.6.43\node_modules\cortico-world-qq-final\src\world.ts",
    r"Cortico\extensions\node_modules\cortico-world-image\src\api.js",
    r"Cortico\extensions\node_modules\cortico-world-image\src\world.js",
    r"Cortico\extensions\node_modules\cortico-world-image\src\tools.js",
]

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
changed = []
for rel in targets:
    p = os.path.join(root, rel)
    if not os.path.exists(p):
        continue
    try:
        s = io.open(p, encoding="utf-8", errors="surrogateescape").read()
    except Exception:
        continue
    variants = [
        OLD,
        OLD.replace("\\", "/"),
        OLD.replace("\\", "\\\\"),
        OLD.replace("/", "\\"),
        OLD.replace("/", "\\\\"),
    ]
    n2 = NEW
    new_variants = [
        n2,
        n2.replace("\\", "/"),
        n2.replace("\\", "\\\\"),
        n2.replace("/", "\\"),
        n2.replace("/", "\\\\"),
    ]
    orig = s
    for a, b in zip(variants, new_variants):
        s = s.replace(a, b)
    if s != orig:
        io.open(p, "w", encoding="utf-8", newline="\n", errors="surrogateescape").write(s)
        changed.append(rel)

print("rebound paths:", OLD, "->", NEW)
for c in changed:
    print("  changed", c)
if not changed:
    print("  (no file changed)")
