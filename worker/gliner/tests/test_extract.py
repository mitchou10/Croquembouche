from app import extract


def line(text, y, x=0.1, w=0.5, h=0.04):
    box = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return {"text": text, "score": 0.9, "points": [{"x": px, "y": py} for px, py in box]}


PAGES = [
    {
        "page": 1,
        "lines": [line("Facture n° 2026-0042", 0.1), line("Client : Marie Dupont", 0.3), line("8 avenue Foch", 0.35)],
    },
    {"page": 2, "lines": [line("Conditions", 0.1), line("Marie Dupont", 0.2)]},
]
ENTITIES = [
    {"id": "e1", "name": "Numéro", "definition": "Le numéro de la facture", "template_id": "t1"},
    {"id": "e2", "name": "Client", "definition": "", "template_id": "t1"},
    {"id": "e3", "name": "Absent", "definition": "La date de naissance", "template_id": "t1"},
]


class FakeModel:
    """Finds a span of the text for a label, as GLiNER answers: `{start, end, label, score}`."""

    def __init__(self, answers):
        self.answers = answers
        self.asked = []

    def predict_entities(self, text, labels, threshold):
        self.asked.append((text, list(labels), threshold))
        out = []
        for label, needle, score in self.answers:
            if label in labels and needle in text:
                start = text.index(needle)
                out.append({"label": label, "text": needle, "start": start, "end": start + len(needle), "score": score})
        return out


def test_the_label_is_the_definition_or_else_the_name():
    assert extract.label_of(ENTITIES[0]) == "Le numéro de la facture"
    assert extract.label_of(ENTITIES[1]) == "Client"


def test_an_entity_is_found_where_its_span_is_on_the_line():
    model = FakeModel([("Le numéro de la facture", "2026-0042", 0.8)])

    [found] = extract.find(PAGES, ENTITIES[:1], model=model, threshold=0.4)

    assert found["entity_id"] == "e1" and found["page"] == 1 and found["text"] == "2026-0042"
    assert model.asked[0][1:] == (["Le numéro de la facture"], 0.4)
    xs = [p["x"] for p in found["points"]]
    # « 2026-0042 » is the end of the 20 characters of the line: the right part of its box (0.1 to 0.6).
    assert min(xs) == 0.1 + 0.5 * 11 / 20 and max(xs) == 0.6
    assert [p["y"] for p in found["points"]] == [0.1, 0.1, 0.14, 0.14]
    assert found["classifications"] == [
        {"template_id": "t1", "confidence": 0.8},
        {"template_id": None, "confidence": 0.2},
    ]


def test_a_span_on_two_lines_is_the_rectangle_around_both():
    model = FakeModel([("Client", "Marie Dupont\n8 avenue Foch", 0.7)])

    [found] = extract.find(PAGES, ENTITIES[1:2], model=model)

    assert found["text"] == "Marie Dupont\n8 avenue Foch"
    assert min(p["y"] for p in found["points"]) == 0.3 and max(p["y"] for p in found["points"]) == 0.39


def test_the_likeliest_answer_of_all_the_pages_is_kept_and_what_is_absent_is_not_given():
    model = FakeModel([("Client", "Marie Dupont", 0.5)])  # found in the page 1 first, then in the page 2: same text
    both = extract.find(PAGES, ENTITIES[1:], model=model)
    assert [f["entity_id"] for f in both] == ["e2"]  # « Absent » is not found

    class Better(FakeModel):
        def predict_entities(self, text, labels, threshold):
            found = super().predict_entities(text, labels, threshold)
            return [{**f, "score": 0.9} for f in found] if text.startswith("Conditions") else found

    [found] = extract.find(PAGES, ENTITIES[1:2], model=Better([("Client", "Marie Dupont", 0.5)]))
    assert found["page"] == 2 and found["classifications"][0]["confidence"] == 0.9


def test_nothing_is_asked_when_there_is_nothing_to_find_or_no_text():
    model = FakeModel([])
    assert (
        extract.find(PAGES, [], model=model) == []
        and extract.find([{"page": 1, "lines": []}], ENTITIES, model=model) == []
    )
    assert model.asked == []


def test_a_long_page_is_read_in_pieces(monkeypatch):
    monkeypatch.setattr(extract.config, "GLINER_CHUNK_WORDS", 4)
    model = FakeModel([])
    extract.find(
        [{"page": 1, "lines": [line("un deux trois", 0.1), line("quatre cinq", 0.2), line("six", 0.3)]}],
        ENTITIES,
        model=model,
    )
    assert [text for text, _, _ in model.asked] == ["un deux trois", "quatre cinq\nsix"]
