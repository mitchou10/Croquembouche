import uuid

from app.services.metrics import Row, count, entity_rows, exact_pages

MODEL = uuid.uuid4()
OTHER = uuid.uuid4()
ENTITY = uuid.uuid4()


def row(status="pending", top=MODEL, confidence=0.9, review=None, page=1, review_page=None, **more):
    return Row(top, page, confidence, status, review, review_page, **more)


def test_nothing_decided_gives_no_ratio():
    counts = count([row(), row()], MODEL)

    assert (counts.reviewed, counts.pending, counts.correct, counts.wrong, counts.missed) == (0, 2, 0, 0, 0)
    assert counts.precision is None and counts.recall is None and counts.f1 is None
    assert counts.mean_confidence_correct is None and counts.mean_confidence_wrong is None


def test_validated_and_annotated_with_the_model_are_right_the_rest_is_wrong():
    rows = [
        row("validated", confidence=0.9),
        row("annotated", review=MODEL, confidence=0.7),
        row("invalidated", confidence=0.5),
        row("annotated", review=OTHER, confidence=0.3),
    ]

    counts = count(rows, MODEL)

    assert (counts.reviewed, counts.correct, counts.wrong) == (4, 2, 2)
    assert counts.precision == 0.5 and counts.recall == 1.0 and counts.f1 == 0.6667
    assert counts.mean_confidence_correct == 0.8 and counts.mean_confidence_wrong == 0.4


def test_what_was_found_by_hand_or_by_correcting_another_prediction_is_missed():
    rows = [
        row("validated"),
        row("annotated", top=MODEL, review=MODEL, source="manual"),  # added by hand
        row("annotated", top=OTHER, review=MODEL),  # a prediction of another model, said to be this one
        row("annotated", top=OTHER, review=OTHER),  # not this model's business
    ]

    counts = count(rows, MODEL)

    assert (counts.correct, counts.missed) == (1, 2)
    assert counts.recall == 0.3333 and counts.precision == 1.0
    assert count(rows, OTHER).missed == 0 and count(rows, OTHER).correct == 1


def test_a_model_found_only_by_hand_has_a_recall_of_zero_and_no_precision():
    counts = count([row("annotated", review=MODEL, source="manual")], MODEL)

    assert counts.precision is None and counts.recall == 0.0 and counts.f1 is None


def test_a_zero_precision_and_recall_has_no_f1():
    counts = count([row("invalidated"), row("annotated", top=OTHER, review=MODEL)], MODEL)

    assert counts.precision == 0.0 and counts.recall == 0.0 and counts.f1 is None


def test_an_entity_is_measured_on_its_own_rows():
    rows = [
        row("validated", entity=ENTITY),
        row("invalidated", entity=ENTITY),
        row("validated", entity=uuid.uuid4()),
        row("annotated", review=MODEL, source="manual", entity=ENTITY),
    ]

    counts = count(entity_rows(rows, ENTITY), MODEL)

    assert (counts.correct, counts.wrong, counts.missed) == (1, 1, 1)


def test_a_page_of_the_model_is_exact_when_the_page_of_the_model_was_right_too():
    rows = [
        row("validated"),
        row("annotated", review=MODEL, page=2, review_page=2),  # right model, and the page it said
        row("annotated", review=MODEL, page=2, review_page=3),  # right model, wrong page
        row("invalidated"),
    ]

    assert exact_pages(rows, MODEL) == 0.6667
    assert exact_pages([row("invalidated")], MODEL) is None
