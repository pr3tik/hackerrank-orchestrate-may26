# Support Triage Agent

Terminal agent that triages support tickets for HackerRank, Claude and Visa using only the provided corpus.

## Run
```
python code/main.py                 # writes support_tickets/output.csv
python code/eval/run_eval.py        # scores against sample_support_tickets.csv
```
Python 3.9+, standard library only (no installs, no API key).

## Pipeline
1. `ingest.py` - walk `data/`, clean, chunk by paragraph (~160 words), tag company/area from folder names
2. `retrieve.py` - BM25 keyword retrieval (pure Python), optional company filter
3. `risk.py` - rule-based gate (no LLM): high-risk categories always escalate; prompt-injection sentences are stripped before retrieval
4. `agent.py` - decision logic: escalate / reply / out-of-scope, request-type classification
5. `respond.py` - extractive answers: every sentence is copied from the corpus, so nothing is hallucinated

## Design decisions
- Escalation is decided by rules, not a model, so malicious ticket text cannot override it.
- Answers are extractive, so they are grounded by construction.
- Thresholds in `agent.py` are tuned against the sample set, not guessed.

## Results
_Fill in after running the eval: status / request_type / product_area accuracy, plus 3 failure cases and what you changed._
