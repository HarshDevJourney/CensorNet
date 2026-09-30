"""
What counts as censorable and what to do about it. Tune thresholds HERE, not in model code.
Key = label produced by a detector.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    category: str
    threshold: float = 0.5        # min model score to act
    action: str = "blur"          # blur | blackout
    margin: float = 0.15          # grow box by this fraction of its size on each side
    shape: str = "rect"           # rect | ellipse


def _nudity(th: float = 0.45, margin: float = 0.2) -> Rule:
    return Rule("nudity", th, "blur", margin)


POLICY: dict[str, Rule] = {
    # NudeNet v3 classes we act on (the *_COVERED / FACE / FEET / BELLY / ARMPITS ones are ignored)
    "FEMALE_BREAST_EXPOSED":    _nudity(),
    "FEMALE_GENITALIA_EXPOSED": _nudity(0.35, 0.25),
    "MALE_GENITALIA_EXPOSED":   _nudity(0.35, 0.25),
    "BUTTOCKS_EXPOSED":         _nudity(),
    "ANUS_EXPOSED":             _nudity(0.35, 0.25),
    # "MALE_BREAST_EXPOSED":    _nudity(0.6),     # off by default (very common, usually acceptable)

    # future detectors register their labels here, e.g.
    # "blood":   Rule("blood", 0.60),
    # "weapon":  Rule("weapon", 0.60),
    # "violence": Rule("violence", 0.70),   # box=None => whole frame
}
