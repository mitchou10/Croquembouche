from app.core import storage


class FakeStorage:
    """The object store, in memory: what is put is what is got, as with the real one."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_object(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        self.objects[key] = (data, content_type)

    def get_object(self, key: str) -> tuple[bytes, str]:
        if key not in self.objects:
            raise storage.ObjectNotFoundError(key)
        return self.objects[key]

    def delete_prefix(self, prefix: str) -> None:
        self.objects = {k: v for k, v in self.objects.items() if not k.startswith(prefix)}
