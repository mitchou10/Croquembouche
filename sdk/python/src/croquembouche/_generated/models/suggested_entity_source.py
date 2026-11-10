from enum import StrEnum


class SuggestedEntitySource(StrEnum):
    BLANK = "blank"
    BOX = "box"
    WIDGET = "widget"

    def __str__(self) -> str:
        return str(self.value)
