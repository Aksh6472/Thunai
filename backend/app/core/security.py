"""Password hashing, JWTs, service-key check, token hashing, PII crypto (SECURITY §3, §7)."""

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.core.errors import TokenExpired, Unauthenticated
from app.core.settings import Settings
from app.domain.enums import Role

JWT_ALGORITHM = "HS256"
_hasher = PasswordHasher()  # argon2id with library defaults
# Verified against when the username is unknown, so both paths take the same time.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


@dataclass(frozen=True)
class Principal:
    """Who is calling. `kind` is "user" (JWT) or "service" (service key)."""

    kind: str
    id: str
    role: Role | None = None
    branch_code: str | None = None

    @property
    def is_service(self) -> bool:
        return self.kind == "service"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(
    *, user_id: str, role: Role, branch_code: str, settings: Settings, now: datetime
) -> tuple[str, int]:
    ttl = timedelta(minutes=settings.jwt_ttl_minutes)
    claims = {
        "sub": user_id,
        "role": role.value,
        "branch": branch_code,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=JWT_ALGORITHM)
    return token, int(ttl.total_seconds())


def decode_access_token(token: str, settings: Settings) -> Principal:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],  # pinned: rejects "none" and algorithm confusion
            options={"require": ["exp", "sub", "role", "jti"]},
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpired() from None
    except jwt.PyJWTError:
        raise Unauthenticated() from None
    try:
        role = Role(claims["role"])
    except ValueError:
        raise Unauthenticated() from None
    return Principal(
        kind="user", id=str(claims["sub"]), role=role, branch_code=claims.get("branch")
    )


def service_key_matches(candidate: str, settings: Settings) -> bool:
    return hmac.compare_digest(candidate.encode(), settings.service_api_key.encode())


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_contact_token() -> str:
    return secrets.token_urlsafe(32)


def hmac_msisdn(msisdn_e164: str, settings: Settings) -> str:
    return hmac.new(settings.hmac_key.encode(), msisdn_e164.encode(), hashlib.sha256).hexdigest()


def encrypt_pii(value: str, settings: Settings) -> str:
    return Fernet(settings.pii_encryption_key.encode()).encrypt(value.encode()).decode()


def decrypt_pii(ciphertext: str, settings: Settings) -> str | None:
    try:
        return Fernet(settings.pii_encryption_key.encode()).decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return None
