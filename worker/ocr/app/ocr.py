"""Reading the text of a page image with PaddleOCR, on the CPU.

A scanned page may be sideways or upside down, and a line of it too: the page is turned upright before it is read, and
what is handed back is placed on the page as it was given (its zones are drawn on that one)."""

import cv2
import numpy as np

from app import config

_engine = None


def get_engine():
    """The PaddleOCR pipeline, made on first use: importing Paddle is slow and a test never needs it."""
    global _engine
    if _engine is None:
        from paddleocr import PaddleOCR

        _engine = PaddleOCR(
            lang=config.OCR_LANG,
            device="cpu",
            cpu_threads=config.OCR_CPU_THREADS or 10,
            # oneDNN fails on some models of Paddle 3 (« ConvertPirAttribute2RuntimeAttribute not support »).
            enable_mkldnn=False,
            # The orientation of the page (0, 90, 180, 270) and of each line (upside down).
            use_doc_orientation_classify=True,
            use_textline_orientation=True,
            # A flat scan has nothing to unwarp: it only costs time.
            use_doc_unwarping=False,
        )
    return _engine


def decode(image: bytes) -> np.ndarray:
    array = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
    if array is None:
        raise ValueError("Not an image")
    return array


def _on_given_page(x: float, y: float, angle: int) -> tuple[float, float]:
    """A point of the upright page (0 to 1) on the page as it was given, which was turned `angle` degrees clockwise."""
    return {0: (x, y), 90: (1 - y, x), 180: (1 - x, 1 - y), 270: (y, 1 - x)}[angle]


def read(image: bytes, engine=None, min_score: float | None = None) -> dict:
    """What a page image says: `{angle, lines: [{text, score, points}]}`, the lines in reading order. `angle` is how
    far the page was turned clockwise (0, 90, 180 or 270); `points` are the four corners of a line as `{x, y}` from 0 to
    1 on the page as given, like the zones of a model."""
    min_score = config.OCR_MIN_SCORE if min_score is None else min_score
    lines, angle = [], 0
    for result in (engine or get_engine()).predict(decode(image)):
        angle = int(result.get("doc_preprocessor_res", {}).get("angle", 0)) % 360
        height, width = result["doc_preprocessor_res"]["output_img"].shape[:2]
        for text, score, polygon in zip(result["rec_texts"], result["rec_scores"], result["rec_polys"], strict=True):
            if text.strip() and score >= min_score:
                points = [
                    dict(zip("xy", (round(v, 4) for v in _on_given_page(px / width, py / height, angle)), strict=True))
                    for px, py in np.asarray(polygon).tolist()
                ]
                lines.append({"text": text, "score": round(float(score), 4), "points": points})
    return {"angle": angle, "lines": lines}
