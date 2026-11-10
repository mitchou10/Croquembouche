from enum import StrEnum


class ShareKind(StrEnum):
    EMAIL = "email"
    GROUP = "group"

    def __str__(self) -> str:
        return str(self.value)
