from app.tasks import ping


def test_ping():
    assert ping() == "pong"
