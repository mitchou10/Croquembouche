"""Where the zones drawn on a model page are on a page of the analysed document.

The page was classified as a page of the model (see `classify`); the two are compared by their keypoints (SIFT, which
does not mind a turned or scaled page), the matches that agree on one homography (RANSAC) tell how the model page lies
on the document, and the zones drawn on the model are carried over with it. A page can hold the model several times:
the keypoints that agreed are set aside and the page is looked at again, until nothing sane is left."""

import io
import math
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

# Pages are looked at no bigger than this (the zones are fractions of the page, so the size does not matter to them).
MAX_SIDE = 1200
# A match is kept when its best candidate is clearly better than the second (Lowe's ratio test).
RATIO = 0.75
MIN_MATCHES = 12
# How far (in pixels of the resized page) a point may land from where the homography puts it, to agree with it.
REPROJECTION_THRESHOLD = 4.0
MIN_INLIERS = 12
MIN_INLIER_RATIO = 0.25
# How much a model page may be scaled on the document (a side), and how much its sides may be out of proportion.
SCALE_RANGE = (0.2, 5.0)
MAX_SKEW = 3.0
MAX_INSTANCES = 8


@dataclass
class Located:
    """A model page found on the page of the document: how sure that is, and where each zone of the model went (the
    points are fractions of the page of the document, in the order of the zones given)."""

    confidence: float
    inliers: int
    zones: list[list[dict[str, float]]]


def _gray(data: bytes) -> np.ndarray:
    image = Image.open(io.BytesIO(data)).convert("L")
    scale = min(1.0, MAX_SIDE / max(image.size))
    if scale < 1:
        image = image.resize((round(image.width * scale), round(image.height * scale)))
    return np.asarray(image)


def _is_convex(quad: np.ndarray) -> bool:
    signs = set()
    for i in range(4):
        a, b, c = quad[i], quad[(i + 1) % 4], quad[(i + 2) % 4]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        signs.add(cross > 0)
    return len(signs) == 1


def _is_sane(homography: np.ndarray, shape: tuple[int, int]) -> bool:
    """Whether the model page can lie on the document the way the homography says: seen from the front or at an angle,
    not mirrored, not squashed, not shrunk to a speck or blown up out of reason."""
    height, width = shape
    corners = np.float32([[0, 0], [width, 0], [width, height], [0, height]]).reshape(-1, 1, 2)
    quad = cv2.perspectiveTransform(corners, homography).reshape(4, 2)
    if not np.isfinite(quad).all() or not _is_convex(quad):
        return False
    # Convex, and wound the way the model page is: a mirrored page is wound the other way.
    area = 0.5 * sum(quad[i][0] * quad[(i + 1) % 4][1] - quad[(i + 1) % 4][0] * quad[i][1] for i in range(4))
    if area <= 0:
        return False
    scale = math.sqrt(area / (width * height))
    if not SCALE_RANGE[0] <= scale <= SCALE_RANGE[1]:
        return False
    sides = [float(np.linalg.norm(quad[(i + 1) % 4] - quad[i])) for i in range(4)]
    if max(sides[0] / sides[2], sides[2] / sides[0], sides[1] / sides[3], sides[3] / sides[1]) > MAX_SKEW:
        return False
    # Wider or taller than the model page is: how much more one way than the other.
    stretch = ((sides[0] + sides[2]) / width) / ((sides[1] + sides[3]) / height)
    return 1 / MAX_SKEW <= stretch <= MAX_SKEW


def _confidence(inliers: int, matches: int, error: float) -> float:
    """From how many matches agree (more is surer, and saturates), what share of the matches they are, and how close
    they land to where the homography puts them."""
    return (inliers / (inliers + 10)) * (inliers / matches) * math.exp(-error / REPROJECTION_THRESHOLD / 2)


def locate(template_page: bytes, page: bytes, zones: list[list[dict[str, float]]]) -> list[Located]:
    """Every place the model page lies on the page of the document, the surest first, with the zones carried over.
    Nothing when the page is not that of the model (or only looks like it)."""
    template = _gray(template_page)
    target = _gray(page)
    sift = cv2.SIFT_create()
    template_points, template_descriptors = sift.detectAndCompute(template, None)
    target_points, target_descriptors = sift.detectAndCompute(target, None)
    if template_descriptors is None or target_descriptors is None or len(template_points) < MIN_MATCHES:
        return []

    matcher = cv2.BFMatcher()
    available = np.ones(len(target_points), dtype=bool)
    found: list[Located] = []

    for _ in range(MAX_INSTANCES):
        indexes = np.flatnonzero(available)
        if len(indexes) < MIN_MATCHES:
            break
        # Each keypoint of the document looks for its match in the model, not the other way round: a model that
        # is twice on the page has every keypoint twice there, and none would pass the ratio test from the model's side.
        pairs = matcher.knnMatch(target_descriptors[indexes], template_descriptors, k=2)
        good = [p[0] for p in pairs if len(p) == 2 and p[0].distance < RATIO * p[1].distance]
        if len(good) < MIN_MATCHES:
            break
        source = np.float32([template_points[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        destination = np.float32([target_points[indexes[m.queryIdx]].pt for m in good]).reshape(-1, 1, 2)
        homography, mask = cv2.findHomography(source, destination, cv2.RANSAC, REPROJECTION_THRESHOLD)
        if homography is None:
            break
        agreeing = mask.ravel().astype(bool)
        inliers = int(agreeing.sum())
        # The keypoints that agreed belong to this instance, sane or not: they are not looked at again.
        for m, agrees in zip(good, agreeing, strict=True):
            if agrees:
                available[indexes[m.queryIdx]] = False
        if inliers < MIN_INLIERS or inliers / len(good) < MIN_INLIER_RATIO:
            break
        if not _is_sane(homography, template.shape):
            continue
        projected = cv2.perspectiveTransform(source[agreeing], homography)
        error = float(np.linalg.norm(projected - destination[agreeing], axis=2).mean())
        found.append(
            Located(
                confidence=_confidence(inliers, len(good), error),
                inliers=inliers,
                zones=[_carry(homography, zone, template.shape, target.shape) for zone in zones],
            )
        )
    return sorted(found, key=lambda f: -f.confidence)


def _carry(
    homography: np.ndarray, zone: list[dict[str, float]], template_shape: tuple[int, int], target_shape: tuple[int, int]
) -> list[dict[str, float]]:
    """A zone drawn on the model page (fractions of it) as it lies on the page of the document (fractions of that)."""
    (template_height, template_width), (target_height, target_width) = template_shape, target_shape
    points = np.float32([[p["x"] * template_width, p["y"] * template_height] for p in zone]).reshape(-1, 1, 2)
    moved = cv2.perspectiveTransform(points, homography).reshape(-1, 2)
    return [
        {"x": round(min(max(x / target_width, 0.0), 1.0), 4), "y": round(min(max(y / target_height, 0.0), 1.0), 4)}
        for x, y in moved
    ]
