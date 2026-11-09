import os
import re

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.environ.get("TEMPLATE_MATCHING_QUEUE_NAME", "template_matching")

# The vector store, and what makes the vectors: switching the embedding model changes the size of the vectors, so each
# model has a collection of its own. An administrator deletes those of models no longer used (`drop_old_collections`).
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "croquembouche-templates")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "google/siglip2-base-patch16-224")
EMBEDDING_CACHE_DIR = os.environ.get("EMBEDDING_CACHE_DIR") or None

# The object store the page images are read from (RustFS locally, S3 elsewhere).
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:9000") or None
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "rustfsadmin")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "rustfsadmin")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_BUCKET = os.environ.get("AWS_BUCKET", "croquembouche-documents")


def collection_name() -> str:
    """The collection of the current embedding model: « croquembouche-templates--google-siglip2-base-patch16-224 »."""
    return f"{QDRANT_COLLECTION}--{re.sub(r'[^a-z0-9]+', '-', EMBEDDING_MODEL.lower()).strip('-')}"


# How similarities become confidences (see `classify`). Without a set of documents to measure against these are first
# guesses, hence settings: a page whose best look-alike scores `OTHER_SCORE` is as likely « other » as that page, and
# the lower `TEMPERATURE` is, the more a small gap between two pages counts.
OTHER_SCORE = float(os.environ.get("CLASSIFY_OTHER_SCORE", "0.85"))
TEMPERATURE = float(os.environ.get("CLASSIFY_TEMPERATURE", "0.02"))
# How many points a page asks for: all the rotations of every page of the models of an analysis.
NEIGHBOURS = int(os.environ.get("CLASSIFY_NEIGHBOURS", "256"))
# Two pages of models that look like each other at least this much are linked in the graph of a search.
SEARCH_LINK_MIN = float(os.environ.get("SEARCH_LINK_MIN", "0.9"))

# Where a result is handed back to, and the key that proves it is the worker's (the backend refuses any without it).
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")

# What a use consumed is measured with CodeCarbon, around the matching of the document: the electricity of the process
# that did it and the CO2 that electricity made in the country. A measure that fails never fails the use.
MEASURE_CONSUMPTION = os.environ.get("MEASURE_CONSUMPTION", "1") != "0"
COUNTRY_ISO_CODE = os.environ.get("COUNTRY_ISO_CODE", "FRA")
# « process » is the power of the worker's process; « machine » the whole host's, which is too much when it is shared.
CONSUMPTION_TRACKING_MODE = os.environ.get("CONSUMPTION_TRACKING_MODE", "process")
