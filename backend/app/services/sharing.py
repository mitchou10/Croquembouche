"""Who a thing is shared with, by e-mail address or group: what an analysis and a model of the catalogue have in
common. An address is personal data, so shares are kept encrypted and found through a blind index."""

import re
from collections.abc import Callable

from app.core.crypto import blind_index
from app.core.security.factory import RequestContext
from app.models.catalogue import Template
from app.schemas.sharing import Share

EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class ShareError(ValueError):
    """A share that cannot be kept; the message says why, for the person who sent it."""


def group_name(path: str) -> str:
    """A group as Keycloak names it in a token is its path (« /direction/paris »): people know it without the slash."""
    return path.strip("/")


def fingerprint(kind: str, value: str) -> str:
    return blind_index(f"{kind}:{value}")


def groups_of(user: RequestContext) -> list[str]:
    """The groups of the person, as their token says."""
    return [group_name(g) for g in user.groups if group_name(g)]


def hashes_of(user: RequestContext) -> set[str]:
    """What a share must match to be for this person: their groups and their address."""
    hashes = {fingerprint("group", name.lower()) for name in groups_of(user)}
    if user.email:
        hashes.add(fingerprint("email", user.email.lower()))
    return hashes


def build[T](user: RequestContext, shares: list[Share], make: Callable[..., T]) -> list[T]:
    """The shares to keep, made with `make(kind=, value=, value_hash=)`: an address must look like one, a group must be
    one the person belongs to (an administrator can name any), and the same one twice is kept once."""
    made: dict[str, T] = {}
    for share in shares:
        if share.kind == "email":
            if not EMAIL.match(share.value):
                raise ShareError(f"« {share.value} » n’est pas une adresse e-mail.")
            value = share.value.lower()
        else:
            name = next((g for g in groups_of(user) if g.lower() == share.value.lower()), None)
            if name is None and not user.is_admin:
                raise ShareError(f"Vous n’êtes pas membre du groupe « {share.value} ».")
            value = name or share.value
        digest = fingerprint(share.kind, value.lower())
        made.setdefault(digest, make(kind=share.kind, value=value, value_hash=digest))
    return list(made.values())


def can_see(user: RequestContext, template: Template) -> bool:
    """Whether a model is for this person: its owner, an administrator, anyone when it is public, or whoever it is
    shared with. A sub-model goes with its model, and the owner of either sees it."""
    root = template.parent or template
    if user.is_admin or user.user_id in (template.owner_id, root.owner_id) or root.visibility == "public":
        return True
    return root.visibility == "shared" and any(s.value_hash in hashes_of(user) for s in root.shares)
