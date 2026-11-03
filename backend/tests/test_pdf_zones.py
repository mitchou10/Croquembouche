import pymupdf
import pytest

from app.services import pdf_zones


def _form(*fields, rotation: int = 0) -> bytes:
    """A PDF whose fields are given as (name, type, rect, label), with a text next to the first one."""
    document = pymupdf.open()
    page = document.new_page(width=400, height=600)
    page.insert_text((50, 64), "Nom du demandeur", fontsize=11)
    for name, kind, rect, label in fields:
        widget = pymupdf.Widget()
        widget.field_name, widget.field_type, widget.field_label = name, kind, label
        widget.rect = pymupdf.Rect(*rect)
        page.add_widget(widget)
    if rotation:
        page.set_rotation(rotation)
    return document.tobytes()


def _drawn(draw, rotation: int = 0) -> bytes:
    document = pymupdf.open()
    page = document.new_page(width=400, height=600)
    draw(page)
    if rotation:
        page.set_rotation(rotation)
    return document.tobytes()


TEXT, CHECK, RADIO, BUTTON = (
    pymupdf.PDF_WIDGET_TYPE_TEXT,
    pymupdf.PDF_WIDGET_TYPE_CHECKBOX,
    pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON,
    pymupdf.PDF_WIDGET_TYPE_BUTTON,
)


def _corners(suggestion):
    first, _, third, _ = suggestion.points
    return first["x"], first["y"], third["x"], third["y"]


def test_a_form_gives_one_suggestion_per_field_with_its_zone():
    found = pdf_zones.suggest(
        _form(("nom", TEXT, (180, 50, 350, 70), ""), ("accepte", CHECK, (50, 140, 64, 154), "J'accepte"))
    )

    assert [(s.source, s.type, s.page) for s in found] == [("widget", "text", 1), ("widget", "yes_no", 1)]
    assert _corners(found[0]) == (0.45, 0.0833, 0.875, 0.1167)  # fractions of the 400 x 600 page
    assert found[1].name == "J'accepte"


def test_a_field_is_named_by_its_label_then_by_the_text_beside_it_then_by_its_own_name():
    found = pdf_zones.suggest(
        _form(
            ("a", TEXT, (50, 100, 200, 120), "Prénom"),  # its label
            ("topmostSubform[0].Page1[0].nom[0]", TEXT, (200, 50, 380, 70), ""),  # the text on its left
            ("topmostSubform[0].Page1[0].ville_naissance[0]", TEXT, (50, 300, 200, 320), ""),  # only its name
        )
    )

    assert [s.name for s in found] == ["Nom du demandeur", "Prénom", "ville naissance"]


def test_a_date_an_amount_and_a_percentage_are_recognised_by_their_names():
    found = pdf_zones.suggest(
        _form(
            ("a", TEXT, (50, 100, 200, 120), "Date de naissance"),
            ("b", TEXT, (50, 150, 200, 170), "Montant en euros"),
            ("c", TEXT, (50, 200, 200, 220), "Taux"),
        )
    )

    assert [s.type for s in found] == ["date", "amount", "percentage"]


def test_the_buttons_of_a_radio_group_are_one_suggestion_and_a_push_button_none():
    found = pdf_zones.suggest(
        _form(
            ("choix", RADIO, (50, 260, 64, 274), "oui"),
            ("choix", RADIO, (50, 290, 64, 304), "non"),
            ("envoyer", BUTTON, (50, 400, 120, 420), "Envoyer"),
        )
    )

    assert [s.name for s in found] == ["choix"]
    assert _corners(found[0]) == (0.125, 0.4333, 0.16, 0.5067)  # over both buttons


def test_a_field_too_small_to_write_in_is_left_out():
    assert pdf_zones.suggest(_form(("a", TEXT, (50, 100, 52, 102), "Rien"))) == []


def test_the_zones_follow_a_rotated_page_as_it_is_shown():
    stored = pdf_zones.suggest(_form(("nom", TEXT, (180, 50, 350, 70), "Nom")))
    turned = pdf_zones.suggest(_form(("nom", TEXT, (180, 50, 350, 70), "Nom"), rotation=90))

    assert _corners(stored[0]) == (0.45, 0.0833, 0.875, 0.1167)
    # Turned a quarter, the page is 600 wide and 400 high: x' = 600 - y, y' = x.
    assert _corners(turned[0]) == (0.8833, 0.45, 0.9167, 0.875)


def test_blanks_and_boxes_are_named_by_the_text_beside_or_above_them():
    def draw(page):
        page.insert_text((50, 60), "Nom :", fontsize=11)
        page.draw_line((90, 62), (300, 62))  # a blank
        page.insert_text((50, 100), "Montant total", fontsize=11)
        page.draw_rect(pymupdf.Rect(140, 88, 250, 106))  # a box
        page.insert_text((70, 150), "J'accepte", fontsize=11)
        page.draw_rect(pymupdf.Rect(50, 140, 62, 152))  # a check box, named by what follows it
        page.insert_text((300, 400), "Légende", fontsize=9)
        page.draw_rect(pymupdf.Rect(300, 410, 380, 430))  # named by what is above it

    found = pdf_zones.suggest(_drawn(draw))

    assert [(s.source, s.type, s.name) for s in found] == [
        ("blank", "text", "Nom"),
        ("box", "amount", "Montant total"),
        ("box", "yes_no", "J'accepte"),
        ("box", "text", "Légende"),
    ]
    assert _corners(found[0]) == (0.225, 0.08, 0.75, 0.1033)  # the strip above the line


def test_what_nobody_names_or_is_not_a_field_is_left_out():
    def draw(page):
        page.insert_text((50, 200), "TITRE DE LA SECTION", fontsize=14)
        page.draw_line((50, 204), (250, 204))  # an underline
        page.draw_rect(pymupdf.Rect(50, 300, 150, 330))  # a box with no label
        page.draw_rect(pymupdf.Rect(50, 400, 60, 700), fill=(0.9, 0.9, 0.9), color=None)  # a background
        page.draw_line((10, 500), (20, 500))  # a stroke too short to write on
        page.draw_rect(pymupdf.Rect(200, 220, 380, 500))  # a panel, far too high for a field

    assert pdf_zones.suggest(_drawn(draw)) == []


def test_a_form_field_and_the_box_drawn_around_it_are_one_suggestion():
    def draw(page):
        page.insert_text((50, 64), "Nom", fontsize=11)
        page.draw_rect(pymupdf.Rect(90, 52, 300, 72))
        widget = pymupdf.Widget()
        widget.field_name, widget.field_type, widget.rect = "nom", TEXT, pymupdf.Rect(92, 54, 298, 70)
        page.add_widget(widget)

    found = pdf_zones.suggest(_drawn(draw))

    assert [(s.source, s.name) for s in found] == [("widget", "Nom")]


def test_a_plain_text_pdf_suggests_nothing_and_neither_does_what_is_not_a_pdf():
    assert pdf_zones.suggest(_drawn(lambda page: page.insert_text((50, 60), "Un texte", fontsize=11))) == []
    assert pdf_zones.suggest(b"not a pdf") == []


def test_a_pdf_with_a_password_suggests_nothing():
    document = pymupdf.open()
    document.new_page()
    locked = document.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="secret")

    assert pdf_zones.suggest(locked) == []


def test_there_are_at_most_a_hundred_and_in_reading_order(monkeypatch):
    def draw(page):
        for row in range(30):
            page.insert_text((20, 20 + row * 18), f"Ligne {row}", fontsize=9)
            page.draw_line((70, 22 + row * 18), (150, 22 + row * 18))
            page.draw_line((200, 22 + row * 18), (300, 22 + row * 18))

    found = pdf_zones.suggest(_drawn(draw))
    monkeypatch.setattr(pdf_zones, "MAX_SUGGESTIONS", 5)
    capped = pdf_zones.suggest(_drawn(draw))

    assert len(found) >= 30 and len(capped) == 5
    tops = [s.points[0]["y"] for s in found]
    assert tops == sorted(tops)


@pytest.mark.parametrize("pages", [2])
def test_every_page_of_a_form_is_looked_at(pages):
    document = pymupdf.open()
    for number in range(pages):
        page = document.new_page(width=400, height=600)
        widget = pymupdf.Widget()
        widget.field_name, widget.field_type, widget.rect = f"f{number}", TEXT, pymupdf.Rect(50, 50, 200, 70)
        page.add_widget(widget)

    found = pdf_zones.suggest(document.tobytes())

    assert [(s.page, s.name) for s in found] == [(1, "f0"), (2, "f1")]
