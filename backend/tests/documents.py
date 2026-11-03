import io

import pymupdf
from PIL import Image


def png(width: int = 8, height: int = 6) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(out, "PNG")
    return out.getvalue()


def image(fmt: str) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (8, 6), "white").save(out, fmt)
    return out.getvalue()


def pdf(pages: int = 2) -> bytes:
    document = pymupdf.open()
    for number in range(pages):
        document.new_page(width=200, height=100).insert_text((20, 50), f"page {number + 1}")
    return document.tobytes()
