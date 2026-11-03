import hashlib
import hmac

from cryptography.fernet import Fernet, MultiFernet

from app.config import EncryptionSettings

_settings = EncryptionSettings()
_fernet = MultiFernet([Fernet(key) for key in _settings.keys])


def encrypt(value: str) -> bytes:
    return _fernet.encrypt(value.encode())


def decrypt(token: bytes) -> str:
    return _fernet.decrypt(token).decode()


def blind_index(value: str) -> str:
    """A fingerprint to look a value up by without keeping it readable: the same text always gives the same hash, which
    tells nothing of the text without the pepper. An e-mail address is compared in lower case, without spaces."""
    return hmac.new(_settings.BLIND_INDEX_PEPPER.encode(), value.strip().lower().encode(), hashlib.sha256).hexdigest()
