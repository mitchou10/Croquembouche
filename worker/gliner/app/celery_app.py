from celery import Celery

from app import config

celery_app = Celery("croquembouche_gliner", broker=config.REDIS_URL, backend=config.REDIS_URL)

celery_app.conf.update(
    task_default_queue=config.QUEUE_NAME,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

from app import tasks  # noqa: E402,F401
