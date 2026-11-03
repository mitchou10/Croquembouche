"""The way to the template_matching worker: a Celery client that only sends messages (the worker does the work)."""

from celery import Celery

QUEUE = "template_matching"


def make_client(broker_url: str) -> Celery:
    client = Celery("croquembouche_backend", broker=broker_url)
    # Do not hang a request on a broker that is down: a few quick tries, then give up.
    client.conf.update(
        broker_connection_timeout=2,
        broker_connection_retry=False,
        broker_transport_options={"socket_timeout": 2, "socket_connect_timeout": 2},
        task_publish_retry_policy={"max_retries": 1, "interval_start": 0, "interval_step": 0.2, "interval_max": 0.5},
    )
    return client
