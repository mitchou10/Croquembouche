from enum import StrEnum


class RunOutFileDecisionType0(StrEnum):
    DELETED = "deleted"
    KEPT = "kept"

    def __str__(self) -> str:
        return str(self.value)
