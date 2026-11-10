from enum import StrEnum


class ReviewStatus(StrEnum):
    ANNOTATED = "annotated"
    INVALIDATED = "invalidated"
    PENDING = "pending"
    VALIDATED = "validated"

    def __str__(self) -> str:
        return str(self.value)
