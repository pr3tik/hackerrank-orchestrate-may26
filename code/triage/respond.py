"""Step 5: grounded, extractive answers. Every sentence is copied from the corpus, so nothing is invented."""
import re

from .retrieve import tokenize

ESCALATE_MSG = (
    "Thank you for reaching out. Your request involves a sensitive or account-specific matter "
    "that I can't resolve safely from the documentation alone, so I've escalated it to a human support agent."
)
OUT_OF_SCOPE_MSG = (
    "I'm sorry, this request is outside what I can help with. I can only answer questions covered by the "
    "HackerRank, Claude, and Visa support documentation."
)


THANKS_MSG = "You're welcome! If you have any other questions about HackerRank, Claude, or Visa support, just ask."


def extract_answer(query: str, hits, max_sents: int = 3, max_chars: int = 700) -> str:
    q = set(tokenize(query))
    best = hits[0].chunk
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", best.text)          # markdown headings
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)        # [label](url) -> label
    text = re.sub(r"[*_`>]+", "", text)                           # emphasis / quote markers
    title = best.title.strip(" .").lower()
    sents = [s.strip(" -") for s in re.split(r"(?<=[.!?])\s+", text)
             if len(s.split()) >= 6 and s.strip(" .-").lower() != title] or [text[:300]]
    scored = [(len(q & set(tokenize(s))), i, s) for i, s in enumerate(sents)]
    top = sorted(scored, key=lambda x: (-x[0], x[1]))[:max_sents]
    top = [t for t in sorted(top, key=lambda x: x[1]) if t[0] > 0] or scored[:1]
    answer = " ".join(s for _, _, s in top).strip()
    if len(answer) > max_chars:
        answer = answer[:max_chars].rsplit(" ", 1)[0] + "..."
    return f"{answer} (Source: {best.title})"
