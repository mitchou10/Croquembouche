from enum import StrEnum


class TemplateCreateVisibilityType0(StrEnum):
    PRIVATE = "private"
    PUBLIC = "public"
    SHARED = "shared"

    def __str__(self) -> str:
        return str(self.value)
