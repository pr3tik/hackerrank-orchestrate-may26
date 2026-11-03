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


@dataclass
class Hit:
    score: float
    coverage: float  # fraction of distinct query terms found in this chunk (0..1)
    chunk: Chunk


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

    def search(self, query: str, company=None, k=5) -> list:
        q = list(dict.fromkeys(tokenize(query)))
        if not q:
            return []
        want = company.lower() if company and company.lower() != "none" else None
        hits = []
        for i, tf in enumerate(self.tf):
            c = self.chunks[i]
            if want and c.company.lower() != want:
                continue
            score, matched = 0.0, 0
            for t in q:
                f = tf.get(t, 0)
                if not f:
                    continue
                matched += 1
                norm = 1 - self.b + self.b * self.len[i] / self.avg
                score += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * norm)
            if score > 0:
                hits.append(Hit(score, matched / len(q), c))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]
