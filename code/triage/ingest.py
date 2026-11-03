"""Step 1: corpus -> chunks. Walks data/, cleans text, splits into paragraph-based chunks."""
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

TEXT_EXT = {".md", ".txt", ".html", ".htm", ".json"}
MAX_WORDS = 160  # DESIGN DECISION #1: chunk size. Tune against the eval, don't guess.
KNOWN = {"hackerrank": "HackerRank", "claude": "Claude", "visa": "Visa"}


@dataclass
class Chunk:
    text: str
    source: str   # path relative to data/
    company: str  # inferred from top-level folder
    area: str     # sub-folder name if present, else company
    title: str


def _clean_html(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>", "\n\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return html.unescape(raw)


def _json_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _json_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _json_strings(v)


def _read(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    ext = path.suffix.lower()
    if ext in {".html", ".htm"}:
        return _clean_html(raw)
    if ext == ".json":
        try:
            return "\n\n".join(_json_strings(json.loads(raw)))
        except ValueError:
            return raw
    return raw


FRONT = re.compile(r"\A\ufeff?\s*---\s*\n(.*?)\n---\s*(\n|\Z)", re.S)


def _front_matter(text: str):
    """Split YAML front matter off the body so it never reaches retrieval or answers."""
    m = FRONT.match(text)
    if not m:
        return None, text
    t = re.search(r"(?m)^title:\s*(.+?)\s*$", m.group(1))
    return (t.group(1).strip().strip("\"'") if t else None), text[m.end():]


def _clean_md(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)            # images
    text = re.sub(r"(?m)!\S+\.(png|jpe?g|gif|svg|webp)\b", " ", text)  # leftover image names
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)            # [label](url) -> label
    text = re.sub(r"https?://\S+", " ", text)                       # bare urls
    text = re.sub(r"(?m)^_Last modified:.*$", "", text)
    text = re.sub(r"(?m)^[ \t]*Last updated:.*$", "", text)                 # "Last updated: Oct 15, 2025 ..." lines
    text = re.sub(r"\(Last updated [^)]*\)", "", text)
    # headings become their own sentence (no '#', and no glueing onto the next paragraph)
    text = re.sub(r"(?m)^[ \t]*#{1,6}[ \t]*(.+?)[ \t]*$", lambda m: m.group(1) if m.group(1)[-1] in ".?!:" else m.group(1) + ".", text)
    return text


def _title(text: str, path: Path) -> str:
    m = re.search(r"(?m)^title:\s*(.+)$", text) or re.search(r"(?m)^#\s+(.+)$", text)
    if m:
        return m.group(1).strip().strip("\"'")
    return path.stem.replace("-", " ").replace("_", " ")


def _company(name: str) -> str:
    low = name.lower()
    for key, val in KNOWN.items():
        if key in low:
            return val
    return name


def _split(text: str):
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    chunks, cur, n = [], [], 0
    for p in filter(None, paras):
        w = len(p.split())
        if cur and n + w > MAX_WORDS:
            chunks.append(" ".join(cur))
            cur, n = [], 0
        cur.append(p)
        n += w
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def load_corpus(data_dir) -> list:
    root = Path(data_dir)
    chunks = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXT:
            continue
        parts = path.relative_to(root).parts
        company = _company(parts[0]) if len(parts) > 1 else "Unknown"
        area = parts[1] if len(parts) > 2 else company
        fm_title, body = _front_matter(_read(path))
        title = fm_title or _title(body, path)
        for piece in _split(_clean_md(body)):
            chunks.append(Chunk(piece, str(Path(*parts)), company, area, title))
    return chunks
