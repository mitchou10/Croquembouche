from pydantic_settings import BaseSettings, SettingsConfigDict


class RustFsSettings(BaseSettings):
    # RustFS speaks S3: locally it is the object store, elsewhere these point at the real S3.
    AWS_ENDPOINT_URL: str | None = "http://localhost:9000"
    AWS_ACCESS_KEY_ID: str = "rustfsadmin"
    AWS_SECRET_ACCESS_KEY: str = "rustfsadmin"
    AWS_REGION: str = "us-east-1"
    AWS_BUCKET: str = "croquembouche-documents"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")
