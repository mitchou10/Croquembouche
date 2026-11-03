from pydantic_settings import BaseSettings, SettingsConfigDict


class EncryptionSettings(BaseSettings):
    # Fernet keys, comma-separated: the first one encrypts, all of them decrypt - so a key is rotated by putting the
    # new one in front. Dev only default: a real deployment sets its own (`Fernet.generate_key()`).
    DATA_ENCRYPTION_KEYS: str = "taXVm8ZLkywpFy7DSR1sXPjkdUU5GtK9kuOHsxmomz8="
    # Keys the blind indexes (see core/crypto.py): changing it makes every stored hash stop matching.
    BLIND_INDEX_PEPPER: str = "dev-only-pepper-not-for-prod"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")

    @property
    def keys(self) -> list[str]:
        return [key.strip() for key in self.DATA_ENCRYPTION_KEYS.split(",") if key.strip()]
