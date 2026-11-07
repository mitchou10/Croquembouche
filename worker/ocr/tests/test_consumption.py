from types import SimpleNamespace
from unittest.mock import MagicMock

from app import config, consumption


class FakeTracker:
    def __init__(self, fail=False):
        self.fail = fail
        self.tasks = []

    def start_task(self, name):
        self.tasks.append(name)

    def stop_task(self):
        if self.fail:
            raise RuntimeError("no power reading")
        return SimpleNamespace(energy_consumed=0.002, emissions=0.0001, duration=3.0)


def test_what_a_block_consumed_is_measured(monkeypatch):
    monkeypatch.setattr(config, "MEASURE_CONSUMPTION", True)
    tracker = FakeTracker()
    monkeypatch.setattr(consumption, "_get_tracker", lambda: tracker)

    with consumption.measured("run-1") as used:
        pass

    assert tracker.tasks == ["run-1"]
    assert used.value == {"energy_kwh": 0.002, "co2_kg": 0.0001, "duration_s": 3.0}


def test_a_measure_that_fails_never_fails_the_block(monkeypatch):
    monkeypatch.setattr(config, "MEASURE_CONSUMPTION", True)
    monkeypatch.setattr(consumption, "_get_tracker", lambda: FakeTracker(fail=True))
    with consumption.measured("run-1") as used:
        done = True
    assert done and used.value is None

    monkeypatch.setattr(consumption, "_get_tracker", MagicMock(side_effect=RuntimeError("no hardware")))
    with consumption.measured("run-2") as used:
        done = True
    assert used.value is None


def test_nothing_is_measured_when_it_is_turned_off(monkeypatch):
    monkeypatch.setattr(config, "MEASURE_CONSUMPTION", False)
    get = MagicMock()
    monkeypatch.setattr(consumption, "_get_tracker", get)

    with consumption.measured("run-1") as used:
        pass

    assert used.value is None
    get.assert_not_called()


def test_the_error_of_the_block_is_not_hidden_and_what_it_consumed_is_let_go_of(monkeypatch):
    monkeypatch.setattr(config, "MEASURE_CONSUMPTION", True)
    tracker = FakeTracker()
    monkeypatch.setattr(consumption, "_get_tracker", lambda: tracker)

    try:
        with consumption.measured("run-1"):
            raise ValueError("boom")
    except ValueError:
        pass

    assert tracker.tasks == ["run-1"]
