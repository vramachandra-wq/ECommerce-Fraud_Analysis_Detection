"""Password hashing and verification (bcrypt)."""
import bcrypt

_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, stored_password: str) -> bool:
    if not stored_password:
        return False
    if is_hashed(stored_password):
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            stored_password.encode("utf-8"),
        )
    # Legacy plain-text fallback until migration or rehash-on-login completes
    return plain_password == stored_password


def is_hashed(stored_password: str) -> bool:
    return bool(stored_password) and stored_password.startswith(_BCRYPT_PREFIXES)


def upgrade_password_if_needed(
    cursor,
    conn,
    *,
    table: str,
    id_column: str,
    id_value: str,
    plain_password: str,
    stored_password: str,
) -> None:
    """Re-hash legacy plain-text passwords after a successful login."""
    if is_hashed(stored_password):
        return
    new_hash = hash_password(plain_password)
    cursor.execute(
        f"UPDATE {table} SET password = %s WHERE {id_column} = %s",
        (new_hash, id_value),
    )
    conn.commit()
