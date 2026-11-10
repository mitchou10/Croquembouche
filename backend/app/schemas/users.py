from app.schemas.base import CamelModel


class PurgeOut(CamelModel):
    """What was deleted of what a person sent to be analysed."""

    runs: int
    searches: int
    documents: int
