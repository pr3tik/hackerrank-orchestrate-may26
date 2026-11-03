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
