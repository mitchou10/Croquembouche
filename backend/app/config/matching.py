from pydantic_settings import BaseSettings, SettingsConfigDict


class MatchingSettings(BaseSettings):
    # The key the worker proves it is the worker with when it hands a result back. Empty: the endpoint is closed.
    INTERNAL_API_KEY: str = ""
    # A worker that has not said it is alive for this long is down; its tasks are no longer on offer. It is forgotten
    # (with its tasks) after WORKER_PURGE_DAYS without a sign.
    WORKER_HEARTBEAT_TTL_SECONDS: int = 90
    WORKER_PURGE_DAYS: int = 7
    # A use that has not come back after this long (a worker down, a message lost) is ended as failed.
    MATCHING_TIMEOUT_SECONDS: int = 600

    # Whether the text of a document is read (by the OCR worker, beside the matching) for every use.
    OCR_ENABLED: bool = True
    # Whether the entities that have no zone are found in that text (by the GLiNER worker, which must be there).
    GLINER_ENABLED: bool = True

    # The water a kWh costs, to say what a use drank: the average of data centres (their cooling and the making of the
    # electricity). An estimate, not a measure: CodeCarbon does not know the water of a host that is not a cloud's.
    WATER_LITERS_PER_KWH: float = 1.8

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")
