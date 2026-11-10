from enum import StrEnum


class DetectionOutSource(StrEnum):
    ANALYSIS = "analysis"
    MANUAL = "manual"

    def __str__(self) -> str:
        return str(self.value)
