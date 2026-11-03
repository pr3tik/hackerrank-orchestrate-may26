"""Measure the agent on sample_support_tickets.csv. Run after EVERY change. Usage: python code/eval/run_eval.py"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from main import ROOT, field, run  # noqa: E402
from triage.ingest import load_corpus  # noqa: E402
from triage.retrieve import Retriever  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--data", default=str(ROOT / "data"))
ap.add_argument("--sample", default=str(ROOT / "support_tickets" / "sample_support_tickets.csv"))
a = ap.parse_args()

rows = list(csv.DictReader(open(a.sample, newline="", encoding="utf-8-sig")))
preds = run(rows, Retriever(load_corpus(a.data)))

for col in ["status", "request_type", "product_area"]:
    ok = sum(field(r, col).lower() == p[col].lower() for r, p in zip(rows, preds))
    print(f"{col:13s} {ok}/{len(rows)} = {ok / len(rows):.0%}")

print("\nstatus mismatches (expected -> predicted):")
for i, (r, p) in enumerate(zip(rows, preds)):
    if field(r, "status").lower() != p["status"]:
        print(f"  row {i}: {field(r, 'status')} -> {p['status']} | {field(r, 'issue')[:90]!r}\n          why: {p['justification']}")
print("\nconfusion:", Counter((field(r, "status").lower(), p["status"]) for r, p in zip(rows, preds)))

print("\nALL ROWS  (expected | predicted)  status / request_type / product_area")
for i, (r, p) in enumerate(zip(rows, preds)):
    print(f"  row {i}: {field(r,'status')} / {field(r,'request_type')} / {field(r,'product_area')}")
    print(f"         {p['status']} / {p['request_type']} / {p['product_area']}")
print("\nexpected request_type values:", Counter(field(r, "request_type") for r in rows))
print("expected product_area values:", Counter(field(r, "product_area") for r in rows))

from triage.risk import sanitize  # noqa: E402
print("\nDETAIL for rows where request_type or product_area is wrong:")
rt = Retriever(load_corpus(a.data))
for i, (r, p) in enumerate(zip(rows, preds)):
    if field(r, "request_type").lower() == p["request_type"] and field(r, "product_area").lower() == p["product_area"]:
        continue
    q, _ = sanitize(f"{field(r,'subject')}. {field(r,'issue')}".strip(". "))
    hits = rt.search(q, field(r, "company")) or rt.search(q)
    print(f"\n row {i} [{field(r,'company')}] issue: {field(r,'issue')[:220]!r}  subject: {field(r,'subject')[:60]!r}")
    print(f"   expected: type={field(r,'request_type')} area={field(r,'product_area')}  | predicted: type={p['request_type']} area={p['product_area']}")
    for h in hits[:3]:
        print(f"   hit {h.coverage:.2f}  {h.chunk.source}")

print("\nSIGNALS (use these to calibrate thresholds next round): expected type | coverage | strength | top source")
for i, r in enumerate(rows):
    q, _ = sanitize(f"{field(r,'subject')}. {field(r,'issue')}".strip(". "))
    hits = rt.search(q, field(r, "company")) or rt.search(q)
    h = hits[0] if hits else None
    print(f"  row {i}: {field(r,'request_type'):14s} cov={h.coverage if h else 0:.2f} strength={h.strength if h else 0:.2f}  {h.chunk.source if h else '-'}")
