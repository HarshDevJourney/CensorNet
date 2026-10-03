"""Word-level profanity matching (English + Hindi/Hinglish). Word list: app/data/profanity.txt"""
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.config import settings

_DATA = Path(__file__).resolve().parent.parent / "data" / "profanity.txt"
_SUFFIX = r"(?:s|es|ed|er|ers|ing|in|y|z)?"


def _clean(tok: str) -> str:
    """NFKC, lowercase, trim punctuation at the edges (keeps '*' and combining marks)."""
    tok = unicodedata.normalize("NFKC", tok).lower().strip()
    while tok and tok[0] != "*" and unicodedata.category(tok[0])[0] in "PSZ":
        tok = tok[1:]
    while tok and tok[-1] != "*" and unicodedata.category(tok[-1])[0] in "PSZ":
        tok = tok[:-1]
    return tok


def _skeleton(s: str) -> str:
    """Collapse repeated letters so 'fuuuck' == 'fuck' and 'madarchodd' == 'madarchod'."""
    return re.sub(r"(.)\1+", r"\1", s)


@lru_cache(maxsize=1)
def _load() -> tuple[re.Pattern | None, frozenset[str]]:
    files = [_DATA] + ([Path(settings.PROFANITY_FILE)] if settings.PROFANITY_FILE else [])
    latin: list[str] = []
    other: set[str] = set()
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            w = _clean(line.split("#", 1)[0])
            if not w:
                continue
            if w.isascii():
                latin.append(re.escape(_skeleton(w)))
            else:
                other.add(_skeleton(w))
    pattern = re.compile(rf"^(?:{'|'.join(latin)}){_SUFFIX}$") if latin else None
    return pattern, frozenset(other)


def is_profane(word: str) -> bool:
    tok = _clean(word)
    if not tok:
        return False
    if re.search(r"\*{2,}", tok):         # Whisper sometimes masks expletives itself: "f***"
        return True
    pattern, other = _load()
    sk = _skeleton(tok)
    if sk in other:
        return True
    return bool(pattern and tok.isascii() and pattern.match(sk))
