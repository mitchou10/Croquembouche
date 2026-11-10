from enum import StrEnum


class ReviewOutStatus(StrEnum):
    ANNOTATED = "annotated"
    INVALIDATED = "invalidated"
    PENDING = "pending"
    VALIDATED = "validated"

    def __str__(self) -> str:
        return str(self.value)
