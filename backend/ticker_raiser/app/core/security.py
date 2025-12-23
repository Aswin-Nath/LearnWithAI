import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
# import jwt
import jwt

from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS



def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC and return salt$hexhash"""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${dk.hex()}"


def verify_password(plain_password: str,hashed_password: str) -> bool:
    try:
        salt, hexhash = hashed_password.split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt.encode(), 100_000)
    return dk.hex() == hexhash

def hash_token(token: str) -> str:
    """Hash a token for storage in blacklist."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> tuple[str, datetime]:
    """
    Create a JWT access token.
    Returns: (token, expiration_datetime)
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt, expire


def create_refresh_token(data: dict) -> tuple[str, datetime]:
    """
    Create a JWT refresh token.
    Returns: (token, expiration_datetime)
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt, expire


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def generate_jti() -> str:
    """Generate a unique JWT ID (jti)."""
    return str(uuid.uuid4())


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())
