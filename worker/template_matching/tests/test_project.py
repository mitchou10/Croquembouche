import io

import cv2
import numpy as np
import pytest
from PIL import Image

from app.project import _is_sane, locate

SIZE = (700, 990)  # width, height of a model page
# Two zones drawn on the model, as fractions of it.
ZONES = [
    [{"x": 0.10, "y": 0.10}, {"x": 0.50, "y": 0.10}, {"x": 0.50, "y": 0.20}, {"x": 0.10, "y": 0.20}],
    [
        {"x": 0.55, "y": 0.60},
        {"x": 0.90, "y": 0.60},
        {"x": 0.90, "y": 0.75},
        {"x": 0.70, "y": 0.80},
        {"x": 0.55, "y": 0.75},
    ],
]


def form(seed: int, size=SIZE) -> np.ndarray:
    """Something with enough on it to have keypoints: lines of text, boxes and a few blobs, all drawn from a seed."""
    rng = np.random.default_rng(seed)
    width, height = size
    page = np.full((height, width), 245, np.uint8)
    for _ in range(40):
        x, y = int(rng.integers(10, width - 120)), int(rng.integers(10, height - 40))
        word = "".join(chr(int(c)) for c in rng.integers(65, 90, 7))
        cv2.putText(
            page, word, (x, y), cv2.FONT_HERSHEY_SIMPLEX, float(rng.uniform(0.5, 1.2)), int(rng.integers(0, 90)), 2
        )
    for _ in range(25):
        x, y = int(rng.integers(0, width - 80)), int(rng.integers(0, height - 60))
        cv2.rectangle(
            page, (x, y), (x + int(rng.integers(20, 80)), y + int(rng.integers(15, 60))), int(rng.integers(0, 120)), 2
        )
    for _ in range(30):
        cv2.circle(
            page,
            (int(rng.integers(0, width)), int(rng.integers(0, height))),
            int(rng.integers(4, 18)),
            int(rng.integers(0, 150)),
            -1,
        )
    return page


def png(image: np.ndarray) -> bytes:
    out = io.BytesIO()
    Image.fromarray(image).save(out, "PNG")
    return out.getvalue()


def place(template: np.ndarray, canvas: tuple[int, int], transform: np.ndarray, onto: np.ndarray | None = None):
    """The model page on a page of `canvas` size (width, height) under a transform (over `onto`, if given)."""
    base = np.full((canvas[1], canvas[0]), 255, np.uint8) if onto is None else onto.copy()
    warped = cv2.warpPerspective(template, transform, canvas, borderValue=255)
    covered = cv2.warpPerspective(np.full_like(template, 255), transform, canvas, borderValue=0) > 0
    base[covered] = warped[covered]
    return base


def similarity(angle: float, scale: float, shift: tuple[float, float]) -> np.ndarray:
    a = np.deg2rad(angle)
    return np.array(
        [[scale * np.cos(a), -scale * np.sin(a), shift[0]], [scale * np.sin(a), scale * np.cos(a), shift[1]], [0, 0, 1]]
    )


def overlap(found: list[dict[str, float]], expected: list[dict[str, float]], canvas: tuple[int, int]) -> float:
    """Intersection over union of two zones (fractions of a page of `canvas` size)."""
    masks = []
    for zone in (found, expected):
        mask = np.zeros((canvas[1], canvas[0]), np.uint8)
        cv2.fillPoly(mask, [np.int32([[p["x"] * canvas[0], p["y"] * canvas[1]] for p in zone])], 1)
        masks.append(mask.astype(bool))
    return float((masks[0] & masks[1]).sum() / (masks[0] | masks[1]).sum())


def expected(transform: np.ndarray, canvas: tuple[int, int]) -> list[list[dict[str, float]]]:
    out = []
    for zone in ZONES:
        points = np.float32([[p["x"] * SIZE[0], p["y"] * SIZE[1]] for p in zone]).reshape(-1, 1, 2)
        moved = cv2.perspectiveTransform(points, transform).reshape(-1, 2)
        out.append([{"x": float(x / canvas[0]), "y": float(y / canvas[1])} for x, y in moved])
    return out


@pytest.fixture(scope="module")
def template():
    return form(1)


def assert_found(template, transform, canvas, noise=0.0, minimum=0.7):
    page = place(template, canvas, transform)
    if noise:
        page = np.clip(page + np.random.default_rng(3).normal(0, noise, page.shape), 0, 255).astype(np.uint8)
    found = locate(png(template), png(page), ZONES)
    assert len(found) == 1
    for zone, wanted in zip(found[0].zones, expected(transform, canvas), strict=True):
        assert overlap(zone, wanted, canvas) >= minimum
    return found[0]


def test_the_same_page_gives_the_zones_where_they_are(template):
    found = assert_found(template, np.eye(3), SIZE, minimum=0.95)

    assert found.confidence > 0.7


def test_a_page_in_a_larger_one_scaled_down(template):
    assert_found(template, similarity(0, 0.7, (150, 200)), (1000, 1300))


def test_a_page_turned_by_any_angle(template):
    # Each angle with where to put the page so that it stays on the document.
    for angle, shift in ((90, (800, 100)), (180, (800, 900)), (25, (350, 50)), (-40, (200, 650))):
        assert_found(template, similarity(angle, 0.8, shift), (1100, 1100))


def test_a_page_in_perspective(template):
    transform = np.array([[0.8, 0.1, 80], [0.05, 0.85, 60], [0.0002, 0.0001, 1]])

    assert_found(template, transform, (900, 1100))


def test_a_noisy_page(template):
    assert_found(template, similarity(5, 0.9, (40, 30)), (850, 1100), noise=12)


def test_a_cropped_page(template):
    # Only the upper part of the page is on the document: the zone that is there is still found.
    page = place(template, SIZE, np.eye(3))[: int(SIZE[1] * 0.55)]
    found = locate(png(template), png(page), ZONES)

    assert len(found) == 1
    assert overlap(found[0].zones[0], ZONES[0], (SIZE[0], page.shape[0])) < 1.0  # fractions are of the cropped page
    assert found[0].zones[0][0]["y"] == pytest.approx(0.10 * SIZE[1] / page.shape[0], abs=0.02)


def test_a_page_that_is_not_the_model_is_rejected(template):
    assert locate(png(template), png(form(2)), ZONES) == []


def test_a_blank_page_is_rejected(template):
    assert locate(png(template), png(np.full((SIZE[1], SIZE[0]), 255, np.uint8)), ZONES) == []


def test_a_blank_model_page_finds_nothing(template):
    assert locate(png(np.full((SIZE[1], SIZE[0]), 255, np.uint8)), png(template), ZONES) == []


def test_a_page_holding_the_model_twice_finds_both(template):
    canvas = (1500, 1100)
    first = similarity(0, 0.6, (30, 30))
    second = similarity(0, 0.6, (780, 400))
    page = place(template, canvas, second, onto=place(template, canvas, first))
    found = locate(png(template), png(page), ZONES)

    assert len(found) == 2
    for place_wanted in (first, second):
        best = max(overlap(f.zones[0], expected(place_wanted, canvas)[0], canvas) for f in found)
        assert best >= 0.7
    assert found[0].confidence >= found[1].confidence


def test_a_big_page_is_looked_at_smaller_and_the_zones_stay_where_they_are(template):
    big = cv2.resize(template, None, fx=2.5, fy=2.5)
    found = locate(png(template), png(big), ZONES)

    assert len(found) == 1
    assert overlap(found[0].zones[0], ZONES[0], SIZE) >= 0.9


def test_a_mirrored_page_is_not_a_match(template):
    mirrored = place(template, SIZE, np.array([[-1.0, 0, SIZE[0]], [0, 1, 0], [0, 0, 1]]))

    assert locate(png(template), png(mirrored), ZONES) == []


@pytest.mark.parametrize(
    "homography",
    [
        np.diag([0.05, 0.05, 1.0]),  # a speck
        np.diag([9.0, 9.0, 1.0]),  # far too big
        np.diag([1.0, 6.0, 1.0]),  # squashed
        np.array([[1.0, 0, 0], [0, 1, 0], [0.01, 0, 1]]),  # folded over itself
        np.array([[np.nan, 0, 0], [0, 1, 0], [0, 0, 1]]),
    ],
)
def test_a_homography_that_is_not_a_page_is_not_sane(homography):
    assert not _is_sane(homography, (990, 700))


def test_a_homography_that_is_a_page_is_sane():
    assert _is_sane(np.eye(3), (990, 700))
