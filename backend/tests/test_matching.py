from app.services.matching import SimulatedMatcher, TemplateRef

MODELS = [TemplateRef("a", 3), TemplateRef("b", 1), TemplateRef("c", 2)]
# Every page of every model is a class a page of the document could be.
PAGES_OF_MODELS = {("a", 1), ("a", 2), ("a", 3), ("b", 1), ("c", 1), ("c", 2)}


def test_the_same_file_gives_the_same_answer():
    first = SimulatedMatcher().match(MODELS, [b"one page"])
    again = SimulatedMatcher().match(MODELS, [b"one page"])
    other = SimulatedMatcher().match(MODELS, [b"another page"])

    assert first == again
    assert first != other


def test_each_page_of_the_document_is_classified_on_its_own():
    result = SimulatedMatcher().match(MODELS, [b"first", b"second", b"third"])

    assert [p.page for p in result.pages] == [1, 2, 3]
    best = [(p.classifications[0].template_id, p.classifications[0].template_page) for p in result.pages]
    assert len(set(best)) > 1  # not the same answer for every page
    for page in result.pages:
        assert {(c.template_id, c.template_page) for c in page.classifications} == {*PAGES_OF_MODELS, (None, None)}
        assert page.classifications == sorted(page.classifications, key=lambda c: -c.confidence)
        assert 0.62 <= page.classifications[0].confidence <= 0.98
        assert round(sum(c.confidence for c in page.classifications), 2) == 1.0


def test_a_classified_page_is_a_page_of_a_model_or_none_at_all():
    for name in range(20):
        for page in SimulatedMatcher().match(MODELS, [bytes([name])]).pages:
            for c in page.classifications:
                assert (c.template_id is None) == (c.template_page is None)
                if c.template_id is not None:
                    assert 1 <= c.template_page <= {m.id: m.pages for m in MODELS}[c.template_id]


def test_what_is_found_has_every_model_as_a_class_the_likeliest_first_adding_up_to_certainty():
    result = SimulatedMatcher().match(MODELS, [b"x"])

    assert result.found, "a page of these bytes has something in it"
    for found in result.found:
        classes = found.classifications
        assert {c.template_id for c in classes} == {"a", "b", "c", None}
        assert all(c.template_page is None for c in classes)  # an element is of a model, not of one of its pages
        assert classes == sorted(classes, key=lambda c: -c.confidence)
        assert 0.62 <= classes[0].confidence <= 0.98
        assert round(sum(c.confidence for c in classes), 2) == 1.0


def test_a_lone_one_page_model_is_the_only_page_it_can_be_besides_other():
    page = SimulatedMatcher().match([TemplateRef("a")], [b"x"]).pages[0]

    assert {(c.template_id, c.template_page) for c in page.classifications} == {("a", 1), (None, None)}
    nothing = SimulatedMatcher().match([], [b"x"])
    assert nothing.found == []
    assert [(c.template_id, c.confidence) for c in nothing.pages[0].classifications] == [(None, 1.0)]


def test_zones_are_in_the_page_and_in_reading_order_by_page():
    result = SimulatedMatcher().match(MODELS, [b"first", b"second", b"third"])

    assert {f.page for f in result.found} <= {1, 2, 3}
    for found in result.found:
        assert len(found.points) in (4, 5)
        assert all(0 <= p["x"] <= 1 and 0 <= p["y"] <= 1 for p in found.points)
    order = [(f.page, min(p["y"] for p in f.points), min(p["x"] for p in f.points)) for f in result.found]
    assert order == sorted(order)
