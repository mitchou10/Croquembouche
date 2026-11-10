from enum import StrEnum


class AnalysisOutStatus(StrEnum):
    DONE = "done"
    FAILED = "failed"
    RUNNING = "running"

    def __str__(self) -> str:
        return str(self.value)
