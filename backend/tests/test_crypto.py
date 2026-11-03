from app.core import crypto
from app.models.base import EncryptedText
from app.models.user import UserProfile


def test_a_value_is_encrypted_and_decrypted():
    token = crypto.encrypt("alice@example.org")

    assert b"alice" not in token
    assert crypto.decrypt(token) == "alice@example.org"
    assert crypto.encrypt("alice@example.org") != token  # a fresh random IV each time


def test_the_blind_index_is_stable_and_ignores_case_and_spaces():
    assert crypto.blind_index(" Alice@Example.org ") == crypto.blind_index("alice@example.org")
    assert crypto.blind_index("alice@example.org") != crypto.blind_index("bob@example.org")
    assert "alice" not in crypto.blind_index("alice@example.org")


def test_the_column_type_reads_and_writes_plain_text_and_keeps_none():
    column = EncryptedText()

    stored = column.process_bind_param("Ada Lovelace", None)

    assert isinstance(stored, bytes) and b"Ada" not in stored
    assert column.process_result_value(stored, None) == "Ada Lovelace"
    assert column.process_bind_param(None, None) is None
    assert column.process_result_value(None, None) is None


def test_the_personal_data_of_a_profile_sits_in_encrypted_columns():
    columns = UserProfile.__table__.columns

    assert isinstance(columns["email_encrypted"].type, EncryptedText)
    assert isinstance(columns["display_name_encrypted"].type, EncryptedText)
    assert "email" not in columns
