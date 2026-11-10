from enum import StrEnum


class RunOutFindstatus(StrEnum):
    DONE = "done"
    FAILED = "failed"
    NONE = "none"
    RUNNING = "running"
    WAITING = "waiting"

    def __str__(self) -> str:
        return str(self.value)
