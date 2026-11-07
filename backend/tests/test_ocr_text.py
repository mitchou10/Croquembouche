from app.schemas.matching import OcrLine, OcrPage
from app.services.ocr_text import is_read, text_in_zone


def line(text, x, y, w=0.2, h=0.04):
    box = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return OcrLine(text=text, score=0.9, points=[{"x": px, "y": py} for px, py in box])


ZONE = [{"x": 0.1, "y": 0.1}, {"x": 0.6, "y": 0.1}, {"x": 0.6, "y": 0.4}, {"x": 0.1, "y": 0.4}]
PAGES = [
    OcrPage(
        page=1, lines=[line("deux", 0.4, 0.2), line("un", 0.15, 0.2), line("trois", 0.15, 0.3), line("loin", 0.7, 0.8)]
    ),
    OcrPage(page=2, lines=[line("autre page", 0.15, 0.2)]),
]


def test_the_lines_in_the_zone_are_read_in_reading_order():
    assert text_in_zone(PAGES, 1, ZONE) == "un\ndeux\ntrois"


def test_nothing_outside_the_zone_or_on_another_page_is_read():
    assert text_in_zone(PAGES, 1, [{"x": 0.8, "y": 0.0}, {"x": 0.9, "y": 0.0}, {"x": 0.9, "y": 0.1}]) == ""
    assert "autre page" not in text_in_zone(PAGES, 1, ZONE)
    assert text_in_zone(PAGES, 3, ZONE) == ""


def test_a_zone_that_is_not_a_polygon_has_no_text():
    assert text_in_zone(PAGES, 1, ZONE[:2]) == ""


def test_an_image_or_a_table_is_not_read_as_text():
    assert not is_read("image") and not is_read("table")
    assert is_read("text") and is_read("date") and is_read(None)
