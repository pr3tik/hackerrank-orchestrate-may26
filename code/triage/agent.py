"""Step 4: the decision logic. Thresholds are DESIGN DECISION #2 - tune them with eval/run_eval.py."""
import re

from .respond import ESCALATE_MSG, OUT_OF_SCOPE_MSG, extract_answer
from .risk import assess, sanitize

CONF_REPLY = 0.40   # coverage needed to answer a medium-risk ticket
CONF_FLOOR = 0.15   # below this the ticket is not about anything in the corpus

BUG = re.compile(r"\b(error|bug|crash\w*|broken|not working|doesn'?t work|fails?|failed|500|exception|glitch|stuck|down|outage|inaccessible|not accessible)\b", re.I)
FEATURE = re.compile(r"\b(feature request|would (like|love)|please add|add support|wish|could you (add|support)|suggest\w*)\b", re.I)
PLEASANTRY = re.compile(r"^\W*(thanks|thank you|ok|okay|great|hello|hi)\W*$", re.I)


def classify_request(text: str, conf: float) -> str:
    if conf < CONF_FLOOR or PLEASANTRY.match(text.strip()):
        return "invalid"
    if BUG.search(text):
        return "bug"
    if FEATURE.search(text):
        return "feature_request"
    return "product_issue"


def triage(issue: str, subject: str, company: str, retriever) -> dict:
    clean, injected = sanitize(f"{subject}. {issue}".strip(". "))
    risk = assess(clean)
    hits = retriever.search(clean, company) or retriever.search(clean)  # fall back if company filter found nothing
    top = hits[0] if hits else None
    conf = top.coverage if top else 0.0
    rtype = classify_request(clean, conf)
    if risk.level == "high" and rtype == "invalid":
        rtype = "product_issue"  # a real sensitive case is never 'invalid', even if the corpus has no matching doc
    area = top.chunk.area if top else "general"
    notes = []
    if injected:
        notes.append("instruction-like text removed from query")
    if risk.urgent:
        notes.append("urgent wording")

    if risk.level == "high":
        status, resp = "escalated", ESCALATE_MSG
        why = f"High-risk category: {', '.join(risk.reasons)}"
    elif conf < CONF_FLOOR or not top:
        # clearly unrelated to the corpus. Reply out-of-scope; escalate only if it looks like a real support need.
        if rtype == "invalid":
            status, resp, why = "replied", OUT_OF_SCOPE_MSG, "No relevant support documentation found; out of scope"
        else:
            status, resp, why = "escalated", ESCALATE_MSG, "No supporting documentation found for a support-like request"
    elif risk.level == "medium" and conf < CONF_REPLY:
        status, resp = "escalated", ESCALATE_MSG
        why = f"Sensitive ({', '.join(risk.reasons)}) with weak documentation match ({conf:.2f})"
    else:
        status, resp = "replied", extract_answer(clean, hits)
        why = f"Answered from '{top.chunk.title}' ({top.chunk.source}), match {conf:.2f}"
    if notes:
        why += "; " + "; ".join(notes)
    return {"status": status, "product_area": area, "response": resp, "justification": why, "request_type": rtype}
