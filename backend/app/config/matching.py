from pydantic_settings import BaseSettings, SettingsConfigDict


class MatchingSettings(BaseSettings):
    # The key the worker proves it is the worker with when it hands a result back. Empty: the endpoint is closed.
    INTERNAL_API_KEY: str = ""
    # A use that has not come back after this long (a worker down, a message lost) is ended as failed.
    MATCHING_TIMEOUT_SECONDS: int = 600

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")
