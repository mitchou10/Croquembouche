from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from app import config, registry

celery_app = Celery("croquembouche_gliner", broker=config.REDIS_URL, backend=config.REDIS_URL)

celery_app.conf.update(
    task_default_queue=config.QUEUE_NAME,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

from app import tasks  # noqa: E402,F401


@worker_ready.connect
def _declare_tasks(**_):
    """The worker is up: the backend is told which tasks it has, and then that it is alive."""
    registry.start()


@worker_shutdown.connect
def _forget_tasks(**_):
    registry.stop()
