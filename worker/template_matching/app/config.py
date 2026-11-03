import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.environ.get("TEMPLATE_MATCHING_QUEUE_NAME", "template_matching")
