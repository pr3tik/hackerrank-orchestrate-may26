"""Terminal entry point. Usage (from repo root): python code/main.py"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from triage.agent import triage  # noqa: E402
from triage.ingest import load_corpus  # noqa: E402
from triage.retrieve import Retriever  # noqa: E402

OUT_COLS = ["status", "product_area", "response", "justification", "request_type"]
ROOT = Path(__file__).resolve().parent.parent


def field(row: dict, name: str) -> str:
    for k, v in row.items():
        if k and k.strip().lower().replace(" ", "_") == name:
            return (v or "").strip()
    return ""


def run(rows, retriever):
    return [triage(field(r, "issue"), field(r, "subject"), field(r, "company"), retriever) for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--input", default=str(ROOT / "support_tickets" / "support_tickets.csv"))
    ap.add_argument("--output", default=str(ROOT / "support_tickets" / "output.csv"))
    a = ap.parse_args()

    chunks = load_corpus(a.data)
    print(f"Loaded {len(chunks)} chunks from {a.data}")
    retriever = Retriever(chunks)
    with open(a.input, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows, base = list(reader), [c for c in reader.fieldnames if c.strip().lower() not in OUT_COLS]
    results = run(rows, retriever)
    with open(a.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=base + OUT_COLS)
        w.writeheader()
        for r, res in zip(rows, results):
            w.writerow({**{k: r.get(k, "") for k in base}, **res})
    print(f"Wrote {len(results)} rows to {a.output}")


if __name__ == "__main__":
    main()
