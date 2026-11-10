def extract_identity(claims: dict, client_id: str) -> dict | None:
    """Map Keycloak userinfo/token claims to the internal identity shape.

    Roles live under resource_access.<client_id>.roles for a client-scoped
    check, rather than the realm-wide roles every user gets by default.
    """
    user_id = claims.get("sub")
    if not user_id:
        return None

    roles = claims.get("resource_access", {}).get(client_id, {}).get("roles", [])
    return {
        "user_id": user_id,
        "email": claims.get("email", ""),
        "first_name": claims.get("given_name", ""),
        "last_name": claims.get("family_name", ""),
        "roles": roles,
        "is_admin": "admin" in roles or "realm-admin" in roles,
        # Needs a "groups" mapper on the croquembouche-backend client (see docker/keycloak/realm-croquembouche.json);
        # without it the groups are just empty.
        "groups": claims.get("groups", []),
        # Only the token of a service account (client_credentials) has it: Keycloak puts the client in a « clientId »
        # claim. A person's token, an exchanged one included, has none.
        "service_client_id": claims.get("clientId") or "",
    }
