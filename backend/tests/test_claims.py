from app.core.security.claims import extract_identity


def test_identity_reads_the_roles_of_the_client_only():
    claims = {
        "sub": "u1",
        "email": "a@b.c",
        "given_name": "Ada",
        "family_name": "Lovelace",
        "groups": ["/team"],
        "resource_access": {"croquembouche-backend": {"roles": ["admin"]}, "other": {"roles": ["x"]}},
    }

    identity = extract_identity(claims, "croquembouche-backend")

    assert identity == {
        "user_id": "u1",
        "email": "a@b.c",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "roles": ["admin"],
        "is_admin": True,
        "groups": ["/team"],
    }


def test_identity_without_roles_is_not_admin():
    identity = extract_identity({"sub": "u1"}, "croquembouche-backend")

    assert identity["roles"] == [] and identity["is_admin"] is False and identity["groups"] == []


def test_identity_needs_a_subject():
    assert extract_identity({"email": "a@b.c"}, "croquembouche-backend") is None
