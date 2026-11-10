from typing import Annotated, Literal

from pydantic import StringConstraints

from app.schemas.base import CamelModel

MAX_SHARES = 20

ShareValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)]
# Who can see a model: its owner alone, the people and groups it is shared with, or everyone.
Visibility = Literal["private", "shared", "public"]


class Share(CamelModel):
    """Who something is shared with: a person, by e-mail address, or a group, by name."""

    kind: Literal["email", "group"]
    value: ShareValue
