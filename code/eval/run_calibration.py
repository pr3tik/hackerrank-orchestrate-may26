"""Calibrate the invalid-vs-valid signal on eval/extra_tickets.csv (labels written by us, NOT by the grader).
Usage: python code\\eval\\run_calibration.py"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from main import ROOT, field  # noqa: E402
from triage.ingest import load_corpus  # noqa: E402
from triage.retrieve import Retriever  # noqa: E402
from triage.risk import sanitize  # noqa: E402

rt = Retriever(load_corpus(str(ROOT / "data")))
rows = list(csv.DictReader(open(Path(__file__).with_name("extra_tickets.csv"), encoding="utf-8-sig")))
vals = []
for r in rows:
    q, _ = sanitize(f"{field(r,'subject')}. {field(r,'issue')}".strip(". "))
    hits = rt.search(q, field(r, "company")) or rt.search(q)
    h = hits[0] if hits else None
    vals.append((field(r, "expected"), h.coverage if h else 0.0, h.strength if h else 0.0, h.score if h else 0.0, field(r, "issue")[:55]))

print("expected  coverage strength score   issue")
for v in sorted(vals, key=lambda v: (v[0], v[1])):
    print(f"{v[0]:8s}  {v[1]:.2f}     {v[2]:.2f}     {v[3]:6.1f}  {v[4]}")

print()
for name, idx in (("coverage", 1), ("strength", 2), ("score", 3)):
    best = (0, None)
    for t in sorted({v[idx] for v in vals}):
        acc = sum((v[idx] < t) == (v[0] == "invalid") for v in vals) / len(vals)
        if acc > best[0]:
            best = (acc, t)
    print(f"best single threshold on {name:8s}: invalid if < {best[1]:.2f}  -> accuracy {best[0]:.0%} on {len(vals)} tickets")
