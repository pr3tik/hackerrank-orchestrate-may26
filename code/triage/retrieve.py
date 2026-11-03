"""Step 2: BM25 retrieval, pure stdlib. Free, local, debuggable."""
import math
import re
from collections import Counter
from dataclasses import dataclass

from .ingest import Chunk

STOP = set(
    "a an the and or but if of to in on for with at by from is are was were be been am i me my "
    "we our you your it its this that these those do does did can could would should will not no "
    "yes please hi hello thanks thank dear regards have has had get got how what why when where "
    "which who as about so just also".split()
)


def tokenize(text: str) -> list:
    out = []
    for t in re.findall(r"[a-z0-9]+", text.lower()):
        if t in STOP:
            continue
        if len(t) > 4 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]  # crude plural stemming; applied to docs and queries alike
        out.append(t)
    return out


RELEASE_NOTES_PENALTY = 0.6
MONTHS = set("january february april june july august september october november december".split())  # 'may'/'march' left in: ambiguous


@dataclass
class Hit:
    score: float
    coverage: float  # fraction of distinct query terms found in this chunk (0..1)
    chunk: Chunk
    strength: float = 0.0  # same, but weighted by term rarity; unseen terms count as max rarity


class Retriever:
    def __init__(self, chunks, k1=1.5, b=0.75):
        self.chunks = chunks
        self.docs = [tokenize(c.title) * 2 + tokenize(c.text) for c in chunks]  # title boosted x2
        self.tf = [Counter(d) for d in self.docs]
        self.len = [len(d) for d in self.docs]
        self.avg = sum(self.len) / max(len(self.len), 1)
        df = Counter()
        for tf in self.tf:
            df.update(tf.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b
        self.max_idf = max(self.idf.values()) if self.idf else 1.0

    def search(self, query: str, company=None, k=5) -> list:
        q = [t for t in dict.fromkeys(tokenize(query)) if t not in MONTHS and not re.fullmatch(r"(19|20)\d\d", t)]
        if not q:
            return []
        want = company.lower() if company and company.lower() != "none" else None
        total_w = sum(self.idf.get(t, self.max_idf) for t in q)
        hits = []
        for i, tf in enumerate(self.tf):
            c = self.chunks[i]
            if want and c.company.lower() != want:
                continue
            score, matched, matched_w = 0.0, 0, 0.0
            for t in q:
                f = tf.get(t, 0)
                if not f:
                    continue
                matched += 1
                matched_w += self.idf[t]
                norm = 1 - self.b + self.b * self.len[i] / self.avg
                score += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * norm)
            if "release-notes" in c.source.lower():
                score *= RELEASE_NOTES_PENALTY  # changelogs rarely answer how-to questions (hypothesis)
            if score > 0:
                hits.append(Hit(score, matched / len(q), c, matched_w / total_w))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]
