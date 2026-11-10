from enum import StrEnum


class RunOutOcrstatus(StrEnum):
    DONE = "done"
    FAILED = "failed"
    NONE = "none"
    RUNNING = "running"

    def __str__(self) -> str:
        return str(self.value)
