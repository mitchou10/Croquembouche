import os
import re

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.environ.get("TEMPLATE_MATCHING_QUEUE_NAME", "template_matching")

# The vector store, and what makes the vectors: switching the embedding model changes the size of the vectors, so each
# model has a collection of its own (the old one is left alone).
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "croquembouche-templates")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "Qdrant/clip-ViT-B-32-vision")
EMBEDDING_CACHE_DIR = os.environ.get("EMBEDDING_CACHE_DIR") or None

# The object store the page images are read from (RustFS locally, S3 elsewhere).
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:9000") or None
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "rustfsadmin")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "rustfsadmin")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_BUCKET = os.environ.get("AWS_BUCKET", "croquembouche-documents")


def collection_name() -> str:
    """The collection of the current embedding model: « croquembouche-templates--qdrant-clip-vit-b-32-vision »."""
    return f"{QDRANT_COLLECTION}--{re.sub(r'[^a-z0-9]+', '-', EMBEDDING_MODEL.lower()).strip('-')}"


# How similarities become confidences (see `classify`). Without a set of documents to measure against these are first
# guesses, hence settings: a page whose best look-alike scores `OTHER_SCORE` is as likely « other » as that page, and
# the lower `TEMPERATURE` is, the more a small gap between two pages counts.
OTHER_SCORE = float(os.environ.get("CLASSIFY_OTHER_SCORE", "0.85"))
TEMPERATURE = float(os.environ.get("CLASSIFY_TEMPERATURE", "0.02"))
# How many points a page asks for: all the rotations of every page of the models of an analysis.
NEIGHBOURS = int(os.environ.get("CLASSIFY_NEIGHBOURS", "256"))
