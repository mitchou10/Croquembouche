from app.services.matching import SimulatedMatcher

MODELS = ["a", "b", "c"]


def test_the_same_file_gives_the_same_answer():
    first = SimulatedMatcher().match(MODELS, [b"one page"])
    again = SimulatedMatcher().match(MODELS, [b"one page"])
    other = SimulatedMatcher().match(MODELS, [b"another page"])

    assert first == again
    assert first != other


def test_every_class_is_there_the_likeliest_first_and_they_add_up_to_certainty():
    result = SimulatedMatcher().match(MODELS, [b"x"])

    assert result.found, "a page of these bytes has something in it"
    for classes in [result.page, *(f.classifications for f in result.found)]:
        assert {c.template_id for c in classes} == {*MODELS, None}  # the models of the analysis, and « other »
        assert classes == sorted(classes, key=lambda c: -c.confidence)
        assert 0.62 <= classes[0].confidence <= 0.98
        assert round(sum(c.confidence for c in classes), 2) == 1.0


def test_a_lone_model_is_certain_of_itself_and_none_of_other_when_there_is_none():
    assert [c.confidence for c in SimulatedMatcher().match(["a"], [b"x"]).page] != [1.0]  # « other » takes a share
    nothing = SimulatedMatcher().match([], [b"x"])
    assert nothing.found == []
    assert [(c.template_id, c.confidence) for c in nothing.page] == [(None, 1.0)]


def test_zones_are_in_the_page_and_in_reading_order_by_page():
    result = SimulatedMatcher().match(MODELS, [b"first", b"second", b"third"])

    assert {f.page for f in result.found} <= {1, 2, 3}
    for found in result.found:
        assert len(found.points) in (4, 5)
        assert all(0 <= p["x"] <= 1 and 0 <= p["y"] <= 1 for p in found.points)
    order = [(f.page, min(p["y"] for p in f.points), min(p["x"] for p in f.points)) for f in result.found]
    assert order == sorted(order)
