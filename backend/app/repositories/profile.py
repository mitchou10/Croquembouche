from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import blind_index
from app.models.user import UserProfile


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user_id: str, display_name: str | None, email: str | None) -> UserProfile:
        """Creates the profile, or brings it up to date with what Keycloak says now; nothing is written if it is."""
        profile = await self._session.get(UserProfile, user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
            self._session.add(profile)
        elif (profile.display_name, profile.email) == (display_name, email):
            return profile
        profile.display_name = display_name
        profile.email = email
        profile.email_hash = blind_index(email) if email else None
        await self._session.commit()
        return profile
