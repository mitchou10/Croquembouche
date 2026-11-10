from enum import StrEnum


class FileDecisionDecision(StrEnum):
    DELETED = "deleted"
    KEPT = "kept"

    def __str__(self) -> str:
        return str(self.value)
