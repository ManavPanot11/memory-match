"""
auth.py - Authentication helpers for the Memory Match Tiles game.

No GUI imports. Uses only stdlib modules: hashlib, secrets, hmac, re.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Optional


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_PBKDF2_ITERATIONS = 200_000
_PBKDF2_HASH_NAME = "sha256"
_SALT_BYTES = 16          # 16 bytes → 32 hex characters per secrets.token_hex


def hash_password(password: str) -> str:
    """Hash *password* with PBKDF2-HMAC-SHA256 and a fresh random salt.

    The returned string is safe to store in a database or config file.
    Format: ``"<hex_salt>$<hex_digest>"``.

    Args:
        password: Plain-text password supplied by the user.

    Returns:
        A string of the form ``"salt$hash"`` where both parts are lowercase
        hexadecimal strings.

    Example::

        stored = hash_password("hunter2")
        assert "$" in stored
    """
    salt_hex = secrets.token_hex(_SALT_BYTES)   # 32 hex chars = 16 bytes
    salt_bytes = bytes.fromhex(salt_hex)

    dk = hashlib.pbkdf2_hmac(
        hash_name=_PBKDF2_HASH_NAME,
        password=password.encode("utf-8"),
        salt=salt_bytes,
        iterations=_PBKDF2_ITERATIONS,
    )
    hash_hex = dk.hex()
    return f"{salt_hex}${hash_hex}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify *password* against the stored PBKDF2 hash string.

    Uses :func:`hmac.compare_digest` for a constant-time comparison to
    prevent timing attacks.

    Args:
        password:    Plain-text password to verify.
        stored_hash: Value previously returned by :func:`hash_password`.

    Returns:
        ``True`` if the password matches, ``False`` on any error or mismatch.

    Example::

        stored = hash_password("secret")
        assert verify_password("secret", stored) is True
        assert verify_password("wrong",  stored) is False
    """
    try:
        salt_hex, expected_hex = stored_hash.split("$", 1)
        salt_bytes = bytes.fromhex(salt_hex)

        dk = hashlib.pbkdf2_hmac(
            hash_name=_PBKDF2_HASH_NAME,
            password=password.encode("utf-8"),
            salt=salt_bytes,
            iterations=_PBKDF2_ITERATIONS,
        )
        actual_hex = dk.hex()

        return hmac.compare_digest(actual_hex, expected_hex)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")

_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
)


def validate_username(username: str) -> tuple[bool, str]:
    """Validate a prospective username.

    Rules:
    - Leading and trailing whitespace is stripped before validation.
    - Length must be 3–20 characters (after stripping).
    - Allowed characters: letters (A–Z, a–z), digits (0–9), and underscore
      (``_``).

    Args:
        username: Username string to validate (may contain surrounding spaces).

    Returns:
        A tuple ``(ok, message)`` where *ok* is ``True`` and *message* is
        ``""`` on success, or *ok* is ``False`` and *message* describes the
        problem.

    Examples::

        validate_username("Alice_99")  # → (True, "")
        validate_username("ab")        # → (False, "Username must be 3–20 characters long.")
        validate_username("bad name")  # → (False, "Username may only contain letters, digits, and underscores.")
    """
    username = username.strip()

    if len(username) < 3 or len(username) > 20:
        return (False, "Username must be 3-20 characters long.")

    if not _USERNAME_RE.match(username):
        return (
            False,
            "Username may only contain letters, digits, and underscores.",
        )

    return (True, "")


def validate_email(email: str) -> tuple[bool, str]:
    """Validate an email address string.

    Rules:
    - Leading and trailing whitespace is stripped.
    - The address is lowercased before matching.
    - Must match the pattern ``local@domain.tld`` (basic RFC-5321 subset).

    Args:
        email: Email address to validate (may contain surrounding spaces).

    Returns:
        A tuple ``(ok, message)`` where *ok* is ``True`` and *message* is
        ``""`` on success, or *ok* is ``False`` and *message* describes the
        problem.

    Examples::

        validate_email("User@Example.COM")  # → (True, "")
        validate_email("not-an-email")       # → (False, "Please enter a valid email address.")
    """
    email = email.strip().lower()

    if not email:
        return (False, "Email address cannot be empty.")

    if not _EMAIL_RE.match(email):
        return (False, "Please enter a valid email address (e.g. user@example.com).")

    return (True, "")


def validate_password(password: str, confirm: Optional[str] = None) -> tuple[bool, str]:
    """Validate a new password and optional confirmation.

    Rules:
    - Minimum length of 6 characters.
    - If *confirm* is provided, *password* and *confirm* must be identical.
    """
    if not password:
        return (False, "Password is required.")

    if len(password) < 6:
        return (False, "Password must be at least 6 characters long.")

    if confirm is not None and password != confirm:
        return (False, "Passwords do not match. Please try again.")

    return (True, "")
