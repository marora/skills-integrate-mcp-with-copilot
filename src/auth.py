"""Teacher authentication helpers."""

import hashlib
import hmac
import json
import os
import re

PBKDF2_ITERATIONS = 310_000
MIN_PASSWORD_HASH_ITERATIONS = 100_000
MAX_PASSWORD_HASH_ITERATIONS = 2_000_000
PASSWORD_HASH_PATTERN = re.compile(r"^[0-9a-f]{32}$")
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _parse_password_hash(encoded_hash: str) -> tuple[int, bytes, bytes]:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded_hash.split("$")
        iterations = int(iterations_text)
    except (AttributeError, ValueError) as exc:
        raise ValueError("Invalid teacher password hash format") from exc

    if (
        algorithm != "pbkdf2_sha256"
        or not MIN_PASSWORD_HASH_ITERATIONS <= iterations <= MAX_PASSWORD_HASH_ITERATIONS
        or not PASSWORD_HASH_PATTERN.fullmatch(salt_text)
        or not DIGEST_PATTERN.fullmatch(digest_text)
    ):
        raise ValueError("Invalid teacher password hash format")

    return iterations, bytes.fromhex(salt_text), bytes.fromhex(digest_text)


def load_teacher_password_hashes() -> dict[str, str]:
    """Load username-to-PBKDF2-hash mappings from the environment."""
    raw_hashes = os.environ.get("TEACHER_PASSWORD_HASHES", "")
    if not raw_hashes:
        return {}

    try:
        credentials = json.loads(raw_hashes)
    except json.JSONDecodeError as exc:
        raise RuntimeError("TEACHER_PASSWORD_HASHES must contain a JSON object") from exc

    if not isinstance(credentials, dict) or not credentials:
        raise RuntimeError("TEACHER_PASSWORD_HASHES must be a non-empty JSON object")

    for username, encoded_hash in credentials.items():
        if not isinstance(username, str) or not username.strip() or not isinstance(encoded_hash, str):
            raise RuntimeError("Teacher credentials must map non-empty usernames to password hashes")
        try:
            _parse_password_hash(encoded_hash)
        except ValueError as exc:
            raise RuntimeError(f"Invalid password hash configured for teacher {username!r}") from exc

    return credentials


def verify_teacher_password(username: str, password: str, credentials: dict[str, str]) -> bool:
    """Verify a teacher password while doing comparable work for unknown users."""
    encoded_hash = credentials.get(username)
    if encoded_hash is None:
        encoded_hash = (
            f"pbkdf2_sha256${PBKDF2_ITERATIONS}$"
            f"{'0' * 32}${'0' * 64}"
        )

    iterations, salt, expected_digest = _parse_password_hash(encoded_hash)
    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest) and username in credentials
