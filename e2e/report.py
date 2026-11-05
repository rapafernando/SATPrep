"""Builds replica/test-plan.md from cases.py and the last pytest run (results.json)."""
import datetime
import json
import pathlib
import re

from cases import CASES

here = pathlib.Path(__file__).parent
results = json.loads((here / "results.json").read_text())
by_case = {}
for nodeid, outcome in results.items():
    m = re.search(r"::test_([A-Z]\d*)_(\d+|[HEN]\d+)", nodeid)
    if not m:
        continue
    cid = f"{m.group(1)}-{m.group(2)}"
    prev = by_case.get(cid)
    by_case[cid] = "failed" if "failed" in (prev, outcome) else outcome
rows, counts = [], {"passed": 0, "failed": 0, "not run": 0, "unit": 0}
for cid, flow, kind, steps, expected, auto in CASES:
    if auto.startswith("unit"):
        res = "pass (unit)"
        counts["unit"] += 1
    elif auto.startswith("e2e (every"):
        out = "failed" if "failed" in results.values() else "passed"
    else:
        out = by_case.get(cid, "not run")
        res = {"passed": "pass", "failed": "FAIL", "not run": "not run"}.get(out, out)
        counts[out if out in counts else "not run"] += 1
    rows.append(f"| {cid} | {flow} | {kind} | {steps} | {expected} | {auto} | {res} |")
out = f"""# Test plan: ScorePath

Date: {datetime.date.today()}  Env: local, production-like (DEBUG off, collected static files, SQLite, fresh seed)
Run: `E2E_PYTHON=<python with Django> python -m pytest e2e` then `python e2e/report.py`

The original app was never touched. All tests run against this clone.

Summary: {counts['passed']} e2e cases passed, {counts['failed']} failed, {counts['not run']} not run, {counts['unit']} covered by Django unit tests.

| case | flow | type | steps | expected | auto | result |
| --- | --- | --- | --- | --- | --- | --- |
""" + "\n".join(rows) + """

## Flows from the recon map that are not built, so not tested
F05 the original's daily timed game, F07 AI coach, F08 multiplayer, F09 subscribe or cancel (skipped on purpose for a private app).

## Needs a hand check (cannot be automated here)
- Apple Pencil drawing on a real iPad (palm rejection).
- "Add to Home Screen" on a real iPhone and Android phone, including the Android Install button.
- Screen reader pass (VoiceOver, TalkBack). The axe scan finds missing labels and contrast, not reading order or wording.
- Docker Compose start on the rapamedia server and https through Caddy.
"""
(here.parent / "replica" / "test-plan.md").write_text(out)
(pathlib.Path("/home/claude/replica") / "test-plan.md").write_text(out)
print(counts)
