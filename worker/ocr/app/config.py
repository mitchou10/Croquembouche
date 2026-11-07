import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.environ.get("OCR_QUEUE_NAME", "ocr")

# The object store the page images are read from (RustFS locally, S3 elsewhere).
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:9000") or None
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "rustfsadmin")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "rustfsadmin")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_BUCKET = os.environ.get("AWS_BUCKET", "croquembouche-documents")

# The language of the recognition model (« fr » reads latin scripts, « en », « ch », ...). Another language is another
# model, downloaded at build time (see the Dockerfile).
OCR_LANG = os.environ.get("OCR_LANG", "fr")
# Below this confidence a line is dropped.
OCR_MIN_SCORE = float(os.environ.get("OCR_MIN_SCORE", "0.5"))
# The threads Paddle computes with on the CPU (0: its own default).
OCR_CPU_THREADS = int(os.environ.get("OCR_CPU_THREADS", "0"))

# Where a result is handed back to, and the key that proves it is the worker's (the backend refuses any without it).
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")

# What a reading consumed is measured with CodeCarbon, as for the matching: a measure that fails never fails it.
MEASURE_CONSUMPTION = os.environ.get("MEASURE_CONSUMPTION", "1") != "0"
COUNTRY_ISO_CODE = os.environ.get("COUNTRY_ISO_CODE", "FRA")
CONSUMPTION_TRACKING_MODE = os.environ.get("CONSUMPTION_TRACKING_MODE", "process")
