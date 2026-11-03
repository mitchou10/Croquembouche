"""What an analysis finds in a document.

The real matching is the `template_matching` worker's, which does not exist yet: until it does, `SimulatedMatcher`
makes the answer up, deterministically (the same file always gives the same one), in the shape the real one will have.
Whatever replaces it only has to honour `Matcher`."""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

MASK = 0xFFFFFFFF


@dataclass
class Classification:
    """What something could be, and how sure the analysis is (0 to 1). No template is « other »."""

    template_id: str | None
    confidence: float


@dataclass
class Found:
    page: int
    points: list[dict[str, float]]
    classifications: list[Classification]


@dataclass
class MatchResult:
    page: list[Classification]
    found: list[Found]


class Matcher(Protocol):
    def match(self, template_ids: list[str], pages: list[bytes]) -> MatchResult: ...


def _random(seed: int) -> Callable[[], float]:
    """mulberry32: a seeded source of numbers between 0 and 1, the same seed giving the same sequence."""
    state = seed & MASK

    def next_value() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & MASK
        t = state
        t = ((t ^ (t >> 15)) * (t | 1)) & MASK
        t ^= (t + ((t ^ (t >> 7)) * (t | 61) & MASK)) & MASK
        return ((t ^ (t >> 14)) & MASK) / 4294967296

    return next_value


def _seed(*parts: bytes | str | int) -> int:
    digest = hashlib.sha256("|".join(p.hex() if isinstance(p, bytes) else str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:4], "big")


def _classes_for(best: str | None, template_ids: list[str], next_value: Callable[[], float]) -> list[Classification]:
    """Every class something could be, the likeliest first, adding up to 100 %: the analysis is 62 to 98 % sure of the
    best answer, and the rest is shared among the other models of the analysis and « other »."""
    others: list[str | None] = [t for t in template_ids if t != best]
    if best is not None:
        others.append(None)
    # With no other class to share the rest with, the only one is certain.
    top = 62 + int(next_value() * 37) if others else 100
    weights = [next_value() + 0.05 for _ in others]
    total = sum(weights)
    shares = [int((100 - top) * w / total) for w in weights]
    if shares:
        shares[0] += 100 - top - sum(shares)  # what rounding left goes to the first
    classes = [
        Classification(best, top / 100),
        *(Classification(t, s / 100) for t, s in zip(others, shares, strict=True)),
    ]
    return sorted(classes, key=lambda c: -c.confidence)


def _zone(next_value: Callable[[], float]) -> list[dict[str, float]]:
    """Mostly a rectangle, sometimes a polygon with a corner cut, as drawn on a model."""
    w = 0.12 + next_value() * 0.23
    h = 0.06 + next_value() * 0.16
    x = 0.03 + next_value() * (0.94 - w)
    y = 0.03 + next_value() * (0.94 - h)
    if next_value() < 0.35:
        points = [(x, y), (x + w, y), (x + w, y + h * 0.6), (x + w * 0.8, y + h), (x, y + h)]
    else:
        points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return [{"x": round(px, 3), "y": round(py, 3)} for px, py in points]


class SimulatedMatcher:
    def match(self, template_ids: list[str], pages: list[bytes]) -> MatchResult:
        content = b"".join(pages)
        first = _random(_seed("page", content))
        best = template_ids[int(first() * len(template_ids))] if template_ids else None
        page = _classes_for(best, template_ids, first)

        found: list[Found] = []
        for number, image in enumerate(pages, start=1):
            next_value = _random(_seed(image, number))
            for template_id in template_ids:
                for _ in range(int(next_value() * 4)):  # 0 to 3: a model is missing from a page one time in four
                    points = _zone(next_value)
                    found.append(Found(number, points, _classes_for(template_id, template_ids, next_value)))
        # In reading order: by page, then top to bottom and left to right.
        found.sort(key=lambda f: (f.page, min(p["y"] for p in f.points), min(p["x"] for p in f.points)))
        return MatchResult(page=page, found=found)
