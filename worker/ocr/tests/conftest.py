import pytest

from app import config


@pytest.fixture(autouse=True)
def _no_measuring(monkeypatch):
    """No test starts CodeCarbon (it reads the hardware): the tests of the measure turn it on, with a fake tracker."""
    monkeypatch.setattr(config, "MEASURE_CONSUMPTION", False)
