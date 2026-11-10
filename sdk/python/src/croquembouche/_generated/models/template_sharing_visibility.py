from enum import StrEnum


class TemplateSharingVisibility(StrEnum):
    PRIVATE = "private"
    PUBLIC = "public"
    SHARED = "shared"

    def __str__(self) -> str:
        return str(self.value)
