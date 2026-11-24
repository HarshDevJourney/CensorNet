"""
What counts as censorable and what to do about it. Tune thresholds in .env (THRESH_*), not in model code.
Key = label produced by a detector.
"""
from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class Rule:
    category: str                 # nudity | weapon | blood | violence
    threshold: float = 0.5        # min model score to act
    action: str = "blur"          # blur | blackout
    margin: float = 0.15          # grow box by this fraction of its size on each side
    shape: str = "rect"           # rect | ellipse
    min_hits: int = 1             # frames a track must be seen on (unless it touches a chunk edge)


def _nudity(th: float, margin: float = 0.2) -> Rule:
    return Rule("nudity", th, "blur", margin)


POLICY: dict[str, Rule] = {
    # NudeNet v3 classes we act on (*_COVERED / FACE / FEET / BELLY / ARMPITS are ignored)
    "FEMALE_BREAST_EXPOSED":    _nudity(settings.THRESH_NUDITY),
    "FEMALE_GENITALIA_EXPOSED": _nudity(settings.THRESH_NUDITY_GENITALIA, 0.25),
    "MALE_GENITALIA_EXPOSED":   _nudity(settings.THRESH_NUDITY_GENITALIA, 0.25),
    "BUTTOCKS_EXPOSED":         _nudity(settings.THRESH_NUDITY),
    "ANUS_EXPOSED":             _nudity(settings.THRESH_NUDITY_GENITALIA, 0.25),
    # "MALE_BREAST_EXPOSED":    _nudity(0.6),     # off by default (very common, usually acceptable)

    "weapon":   Rule("weapon", settings.THRESH_WEAPON, "blur", 0.25),
    "blood":    Rule("blood", settings.THRESH_BLOOD, "blur", 0.15, min_hits=settings.BLOOD_MIN_HITS),
    "violence": Rule("violence", settings.THRESH_VIOLENCE, "blur", 0.0, min_hits=settings.VIOLENCE_MIN_HITS),
}
