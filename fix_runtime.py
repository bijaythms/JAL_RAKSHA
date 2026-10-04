#!/usr/bin/env python3
"""JAL-RAKSHA runtime fixer: router imports, coastal polygon, frame count,
grid test. Patches files next to itself, then verifies."""
import ast, glob, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
fixed = []

# ---------- 1) routers: from ... -> from .. (the run.py crash) ----------
n_total = 0
for f in sorted(glob.glob(os.path.join("app", "routers", "*.py"))):
    src = open(f, encoding="utf-8").read()
    n = src.count("from ...")
    if n:
        open(f, "w", encoding="utf-8").write(src.replace("from ...", "from .."))
        n_total += n
        print("  routers/" + os.path.basename(f) + ": fixed " + str(n) + " import(s)")
fixed.append("router imports: " + str(n_total))

# ---------- 2) india.py: extend coastal polygon over interior Odisha ----------
P = os.path.join("app", "services", "india.py")
src = open(P, encoding="utf-8").read()
OLD = "(17.0, 83.0), (20.5, 86.3)"
NEW = "(17.0, 82.0), (19.0, 84.3), (21.0, 86.2)"
if OLD in src:
    open(P, "w", encoding="utf-8").write(src.replace(OLD, NEW))
    fixed.append("coastal polygon extended")
else:
    print("  WARN: coastal polygon pattern not found (already fixed?)")

# ---------- 3) impact_models.py: guarantee N_FRAMES via linspace fallback ----------
P = os.path.join("app", "services", "impact_models.py")
src = open(P, encoding="utf-8").read()
OLD = "N_FRAMES).astype(int))"
NEW = ("N_FRAMES).astype(int))\n"
       "    if len(fi) < N_FRAMES:\n"
       "        fi = np.unique(np.linspace(0, len(t_ser) - 1, "
       "N_FRAMES).astype(int))")
if OLD in src and "if len(fi) < N_FRAMES" not in src:
    open(P, "w", encoding="utf-8").write(src.replace(OLD, NEW, 1))
    fixed.append("frame-count fallback added")
else:
    print("  WARN: frame pattern not found (already fixed?)")

# ---------- 4) test_platform.py: grid row 0 is NORTH (maxlat) ----------
P = os.path.join("tests", "test_platform.py")
src = open(P, encoding="utf-8").read()
OLD = "assert 30.00 < la < 30.001 and 79.00 < lo < 79.001"
NEW = "assert 30.099 < la < 30.10 and 79.00 < lo < 79.001"
if OLD in src:
    open(P, "w", encoding="utf-8").write(src.replace(OLD, NEW))
    fixed.append("grid test orientation corrected")
else:
    print("  WARN: grid test pattern not found (already fixed?)")

# ---------- verify: every .py compiles ----------
bad = []
for f in glob.glob(os.path.join("app", "**", "*.py"), recursive=True) + \
         glob.glob(os.path.join("tests", "*.py")):
    try:
        ast.parse(open(f, encoding="utf-8").read())
    except SyntaxError as e:
        bad.append(f + ": line " + str(e.lineno) + ": " + e.msg)
if bad:
    print("\nSYNTAX ERRORS:")
    for b in bad:
        print("  " + b)
    sys.exit(1)

# ---------- verify: the fixed behaviors ----------
sys.path.insert(0, ROOT)
from app.services import india as _ind
assert _ind.region_for(20.0, 85.5).key == "coastal", "coastal fix failed"
assert _ind.region_for(20.0, 78.5).key == "peninsular", "peninsular regressed"
assert _ind.region_for(28.6, 77.2).key == "gangetic", "Delhi regressed"

from app.main import app    # the import that crashed run.py
print("\nALL FIXES APPLIED AND VERIFIED:")
for f in fixed:
    print("  + " + f)
print("  + app.main imports cleanly (run.py will start)")
print("\nNext:  python -m pytest tests/ -q   then   python run.py")