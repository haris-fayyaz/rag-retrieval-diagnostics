"""
Password hashing and JWT helpers for the lightweight auth added in
feature/jwt-auth-rate-limiting. Single hardcoded user, no user table -
see app/core/config.py for APP_USERNAME/APP_PASSWORD_HASH/JWT_* settings.
"""
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone

from app.core.config import settings


def hash_password(password: str) -> str:
    """
    Hash a plaintext password for storage in APP_PASSWORD_HASH.
    - bcrypt salts automatically, the salt is embedded in the output.
    - Run this once, offline, to generate the env var value - never
      call at request time (that's verify_password, below).
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Check a plaintext password against a stored bcrypt hash.
    - Returns False (not an exception) on a malformed stored hash, so a
      bad APP_PASSWORD_HASH fails closed instead of crashing the request.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    """
    Issue a JWT for `subject` (the username), signed with JWT_SECRET.
    - Claims: sub, iat, exp - exactly what the task asks for, nothing
      else (no roles/permissions - out of scope by design).
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """
    Verify a JWT and return its subject (username).
    - Raises jwt.PyJWTError (covers expired/malformed/bad-signature/
      missing-claim) on any failure - the caller maps this to a single
      401, not a different message per failure type (don't leak which
      check failed).
    """
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    try:
        return payload["sub"]
    except KeyError:
        raise jwt.InvalidTokenError("token missing 'sub' claim")