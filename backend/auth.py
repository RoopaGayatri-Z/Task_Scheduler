"""
Authentication + authorization helpers.

- Passwords: salted bcrypt hashes (bcrypt.gensalt() adds a unique salt per hash).
- MFA: TOTP (RFC 6238) - works with Google Authenticator / Microsoft Authenticator.
- Sessions: short-lived signed JWT sent as "Authorization: Bearer <token>".
- Roles: student | faculty | viewer.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
import pyotp
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

import models
from database import get_db

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is not set. Add it to backend/.env (local) or the environment variables (Render)."
    )

JWT_ALGORITHM = "HS256"
TOKEN_LIFETIME_MINUTES = int(os.getenv("TOKEN_LIFETIME_MINUTES", "120"))
ISSUER = "Student Task Scheduler"

# Roles allowed to create / update / delete data. "viewer" is read-only.
WRITE_ROLES = ("student", "faculty")

bearer_scheme = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------ passwords
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # stored value is not a valid bcrypt hash
        return False


# ----------------------------------------------------------------------- TOTP
def new_totp_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(username: str, secret: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=ISSUER)


def verify_totp(secret: str, code: str) -> bool:
    # valid_window=1 tolerates 30 s of clock drift either side
    return pyotp.TOTP(secret).verify(code, valid_window=1)


# ----------------------------------------------------------------------- JWT
def create_access_token(user: models.User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.username,
        "role": user.role,
        "iss": ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_LIFETIME_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if creds is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated: missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM], issuer=ISSUER
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired, please log in again")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(models.User).filter(models.User.username == payload.get("sub")).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


def require_roles(*allowed_roles: str):
    """Dependency factory: 401 if not logged in, 403 if logged in with the wrong role."""

    def checker(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user.role}' is not allowed to perform this action",
            )
        return user

    return checker
