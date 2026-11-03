import redis

from app.config import RedisSettings


class RedisConnector:
    def __init__(self, url: str) -> None:
        self.client = redis.Redis.from_url(url, decode_responses=True)


redis_settings = RedisSettings()
redis_connector = RedisConnector(redis_settings.REDIS_URL)
