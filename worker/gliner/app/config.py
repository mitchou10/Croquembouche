import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.environ.get("GLINER_QUEUE_NAME", "gliner")

# Finding an entity that has no zone in the text (see `extract`): GLiNER, which finds in a text what a label describes.
# The model is part of the image (see the Dockerfile). Below the threshold a span is not taken.
GLINER_MODEL = os.environ.get("GLINER_MODEL", "urchade/gliner_multi-v2.1")
GLINER_THRESHOLD = float(os.environ.get("GLINER_THRESHOLD", "0.4"))
# GLiNER reads about 380 words at a time: a page is cut in pieces of lines of at most this many words.
GLINER_CHUNK_WORDS = int(os.environ.get("GLINER_CHUNK_WORDS", "250"))

# Where a result is handed back to, and the key that proves it is the worker's (the backend refuses any without it).
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")

# What a search consumed is measured with CodeCarbon, as for the matching: a measure that fails never fails it.
MEASURE_CONSUMPTION = os.environ.get("MEASURE_CONSUMPTION", "1") != "0"
COUNTRY_ISO_CODE = os.environ.get("COUNTRY_ISO_CODE", "FRA")
CONSUMPTION_TRACKING_MODE = os.environ.get("CONSUMPTION_TRACKING_MODE", "process")
