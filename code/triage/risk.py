"""Step 3: rule-based safety gate. NO LLM here, so injected text cannot talk it out of escalating."""
import re
from dataclasses import dataclass, field

# HIGH: always escalate. MEDIUM: reply only if retrieval is confident.
HIGH = {
    "fraud_or_unauthorized": r"\b(fraud\w*|unauthori[sz]ed|scam\w*|phish\w*|identity theft)\b",
    "service_outage": r"\b(site|website|platform|service|server)\b.{0,25}\b(down|outage|unavailable)\b|\bnone of the (pages|features)\b|\boutage\b",
    "money_dispute": r"\b(chargeback|dispute[sd]?|charged twice|double[- ]charged|overcharg\w+)\b",
    "legal": r"\b(lawyer|attorney|legal action|lawsuit|sue you|subpoena|gdpr|court)\b",
    "security_report": r"\b(vulnerabilit\w+|exploit\w*|data breach|bug bounty|leaked)\b",
    "account_compromise": r"\b(hacked|compromised|someone (else )?(logged|accessed))\b",
}
MEDIUM = {
    "lost_or_stolen": r"\b(lost|stolen)\b.{0,40}\b(card|cheques?|checks?)\b|\b(card|cheques?|checks?)\b.{0,40}\b(lost|stolen)\b",
    "billing": r"\b(refund\w*|billing|invoice|subscription|payment|charged)\b",
    "account_access": r"\b(locked out|can'?t (log ?in|access)|suspended|banned|reset|2fa|password)\b",
    "assessment_integrity": r"\b(cheat\w*|plagiari\w+|score (dispute|change)|re-?evaluat\w+|retake)\b",
    "permissions": r"\b(permission\w*|admin|remove (a )?user|transfer ownership)\b",
}
INJECTION = re.compile(
    r"(ignore (all |any |the )?(previous|prior|above|earlier)|disregard (the |all |your )?(previous|prior|above|instructions|rules)"
    r"|system prompt|reveal (your|the) (rules|prompt|instructions)|you are now|developer mode|jailbreak"
    r"|pretend (to be|you)|act as (if|an?)|forget (your|all) (rules|instructions))",
    re.I,
)
URGENT = re.compile(r"\b(urgent\w*|asap|immediately|emergency|right now)\b", re.I)


@dataclass
class Risk:
    level: str = "low"  # low | medium | high
    reasons: list = field(default_factory=list)
    urgent: bool = False


def sanitize(text: str):
    """Drop sentences that try to instruct the agent. Returns (clean_text, injection_found)."""
    sents = re.split(r"(?<=[.!?\n])\s+", text)
    kept = [s for s in sents if not INJECTION.search(s)]
    return " ".join(kept).strip(), len(kept) != len(sents)


def assess(text: str) -> Risk:
    r = Risk(urgent=bool(URGENT.search(text)))
    for name, pat in HIGH.items():
        if re.search(pat, text, re.I):
            r.level = "high"
            r.reasons.append(name)
    if r.level != "high":
        for name, pat in MEDIUM.items():
            if re.search(pat, text, re.I):
                r.level = "medium"
                r.reasons.append(name)
    return r
