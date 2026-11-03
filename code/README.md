# Multi-Domain Support Triage Agent (v1: BM25 baseline)

A terminal agent that triages support tickets for HackerRank, Claude and Visa using only the provided corpus in `data/`.
For each ticket it outputs: `status` (replied / escalated), `product_area`, `response`, `justification`, `request_type`.

> **Context:** this is a practice build of the May 2026 HackerRank Orchestrate problem, done after the event ended.
> It is not an official submission.
>
> **AI assistance:** I built this with Claude as a coding assistant, and Claude wrote most of the code.
> What I did myself: [WRITE 2-3 TRUE THINGS HERE: e.g. ran every eval, read the failures, decided what to commit, chose what to fix next].

## Run
```
python code/main.py                 # writes support_tickets/output.csv
python code/eval/run_eval.py        # scores against sample_support_tickets.csv
```
Python 3.9+, standard library only. No API key, no network, fully deterministic.

## How it works
1. `triage/ingest.py` - walks `data/`, cleans markdown/HTML, splits into ~160-word chunks tagged with company and folder.
2. `triage/retrieve.py` - BM25 keyword search (pure Python). Filters by company when given. Release-notes pages are down-weighted. Years and month names are dropped from queries.
3. `triage/risk.py` - rule-based safety gate with no LLM, so ticket text cannot talk it out of escalating.
   High risk (always escalate): fraud/unauthorized activity, legal, security reports, account compromise, service outage.
   Medium risk (escalate unless the documentation match is strong): billing, account access, assessment integrity, permissions, lost/stolen card.
   Instruction-like sentences ("ignore previous instructions...") are stripped before retrieval.
4. `triage/agent.py` - decision logic: escalate / reply / out-of-scope, plus request-type classification.
5. `triage/respond.py` - extractive answers. Every sentence is copied from the corpus, so nothing is invented.

## Results on the 10 provided sample tickets
| Column | Score |
|---|---|
| status | 10/10 |
| request_type | 9/10 |
| product_area | 6/10 |

**Caveat:** these are in-sample numbers. I changed rules after seeing these same 10 rows, so expect lower scores on unseen tickets.

## Known failure modes (v1)
- **Wrong document retrieved** on 3 of 7 real product tickets. Long, messy tickets dilute keyword matching, and generic words pull in unrelated pages.
- **Off-topic detection is unreliable.** Word overlap can't tell "actor in Iron Man" from a real question (coverage 0.17 vs 0.24+ for real tickets, too close to separate). A calibration set of short synthetic tickets was misleading because real tickets are much longer.
- **Visa `product_area` labels are a hypothesis** fitted to 2 sample rows (travel pages -> `travel_support`, else `general_support`).
- **Extractive answers can include sentences that don't answer the question**, since they are chosen by word overlap.

## Next (v2)
Hybrid retrieval: BM25 + local embeddings for semantic matching and out-of-scope detection. I will compare it against these v1 numbers.
