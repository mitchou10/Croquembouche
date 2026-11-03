from app.celery_app import celery_app


@celery_app.task(name="template_matching.ping")
def ping() -> str:
    return "pong"
