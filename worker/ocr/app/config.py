import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.environ.get("OCR_QUEUE_NAME", "ocr")

# The object store the page images are read from (RustFS locally, S3 elsewhere).
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:9000") or None
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "rustfsadmin")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "rustfsadmin")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_BUCKET = os.environ.get("AWS_BUCKET", "croquembouche-documents")

# The models: PP-OCRv6 « tiny » (a few million parameters), run by ONNX Runtime on the CPU, without the Paddle
# framework.
# The tiny recognition model reads 49 languages (not Japanese): there is no language to choose. A bigger one is another
# name (`PP-OCRv6_small_det`, `PP-OCRv6_small_rec`...). They are downloaded at build time (see the Dockerfile).
OCR_DET_MODEL = os.environ.get("OCR_DET_MODEL", "PP-OCRv6_tiny_det")
OCR_REC_MODEL = os.environ.get("OCR_REC_MODEL", "PP-OCRv6_tiny_rec")
# What runs them: `onnxruntime` (the ONNX models, on the CPU), or `paddle` (which needs the `paddlepaddle` package).
OCR_ENGINE = os.environ.get("OCR_ENGINE", "onnxruntime")
# Below this confidence a line is dropped.
OCR_MIN_SCORE = float(os.environ.get("OCR_MIN_SCORE", "0.5"))
# The threads to compute with on the CPU (0: ONNX Runtime's own choice, which suits a small model).
OCR_CPU_THREADS = int(os.environ.get("OCR_CPU_THREADS", "0"))

# Where a result is handed back to, and the key that proves it is the worker's (the backend refuses any without it).
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")

# What a reading consumed is measured with CodeCarbon, as for the matching: a measure that fails never fails it.
MEASURE_CONSUMPTION = os.environ.get("MEASURE_CONSUMPTION", "1") != "0"
COUNTRY_ISO_CODE = os.environ.get("COUNTRY_ISO_CODE", "FRA")
CONSUMPTION_TRACKING_MODE = os.environ.get("CONSUMPTION_TRACKING_MODE", "process")

# This worker tells the backend which tasks it has and that it is alive (see `registry`), every so many seconds. It
# is signed with the same key as a result. REGISTER_TASKS=0 turns it off.
HEARTBEAT_SECONDS = float(os.environ.get("WORKER_HEARTBEAT_SECONDS", "30"))
REGISTER_TASKS = os.environ.get("REGISTER_TASKS", "1") != "0"
# Who made the tasks, as the backend lists them.
WORKER_AUTHOR = os.environ.get("WORKER_AUTHOR", "Croquembouche")


def version() -> str:
    """The version of this worker, which is the one of its tasks: the one of the package, which a release changes."""
    from importlib import metadata

    try:
        return metadata.version("croquembouche-worker-ocr")
    except metadata.PackageNotFoundError:  # run from the sources
        return "0+unknown"
