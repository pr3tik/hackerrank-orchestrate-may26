"""Step 4: the decision logic. Thresholds are DESIGN DECISION #2 - tune them with eval/run_eval.py."""
import re

from .respond import ESCALATE_MSG, OUT_OF_SCOPE_MSG, THANKS_MSG, extract_answer
from .risk import assess, sanitize

CONF_REPLY = 0.40   # coverage needed to answer a medium-risk ticket
CONF_FLOOR = 0.15   # below this the ticket is not about anything in the corpus

BUG = re.compile(r"\b(error|bug|crash\w*|broken|not working|doesn'?t work|fails?|failed|500|exception|glitch|stuck|down|outage|inaccessible|not accessible)\b", re.I)
FEATURE = re.compile(r"\b(feature request|would (like|love)|please add|add support|wish|could you (add|support)|suggest\w*)\b", re.I)
THANKS = re.compile(r"^\W*(thanks|thank you|thankyou|thx)\b", re.I)
GREETING = re.compile(r"^\W*(ok|okay|great|hello|hi|hey)\W*$", re.I)
STILL_ASKING = re.compile(r"\b(but|still|not|n't|cannot|however|issue|problem|error|help me with)\b", re.I)

# Area labels for tickets with no documentation behind them. Each seen ONCE in the 10 sample rows - weak evidence.
AREA_OFF_TOPIC = "conversation_management"


def is_pleasantry(text: str) -> bool:
    t = text.strip()
    if GREETING.match(t):
        return True
    return len(t.split()) <= 8 and "?" not in t and bool(THANKS.match(t)) and not STILL_ASKING.search(t)


def norm_area(a: str) -> str:
    """Sample labels are lowercase_with_underscores; 'hackerrank_community' -> 'community' (seen once, verify)."""
    a = a.lower().replace("-", "_").replace(" ", "_")
    return a[len("hackerrank_"):] if a.startswith("hackerrank_") else a


def classify_request(text: str, conf: float) -> str:
    if is_pleasantry(text) or conf < CONF_FLOOR:
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
    social = is_pleasantry(clean)
    rtype = classify_request(clean, conf)
    if risk.level == "high" and rtype == "invalid":
        rtype = "product_issue"  # a real sensitive case is never 'invalid', even if the corpus has no matching doc
    area = norm_area(top.chunk.area) if top else "general"
    notes = []
    if injected:
        notes.append("instruction-like text removed from query")
    if risk.urgent:
        notes.append("urgent wording")

    if risk.level == "high":
        status, resp = "escalated", ESCALATE_MSG
        why = f"High-risk category: {', '.join(risk.reasons)}"
        if risk.reasons == ["service_outage"]:
            area = ""  # an outage is not a documented product area
    elif social:
        status, resp, area = "replied", THANKS_MSG, ""
        why = "Gratitude or greeting; no support action needed"
    elif conf < CONF_FLOOR or not top:
        # clearly unrelated to the corpus. Reply out-of-scope; escalate only if it looks like a real support need.
        if rtype == "invalid":
            status, resp, why = "replied", OUT_OF_SCOPE_MSG, "No relevant support documentation found; out of scope"
            area = AREA_OFF_TOPIC
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
