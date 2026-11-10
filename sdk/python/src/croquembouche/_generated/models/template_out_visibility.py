from enum import StrEnum


class TemplateOutVisibility(StrEnum):
    PRIVATE = "private"
    PUBLIC = "public"
    SHARED = "shared"

    def __str__(self) -> str:
        return str(self.value)
