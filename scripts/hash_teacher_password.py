"""Generate a PBKDF2 password hash for a teacher account."""

import getpass
import hashlib
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.auth import PBKDF2_ITERATIONS


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username:
        raise SystemExit("Username must not be empty.")

    password = getpass.getpass("Teacher password: ")
    if len(password) < 12:
        raise SystemExit("Choose a password with at least 12 characters.")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    encoded_hash = (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"
    )
    print(json.dumps({username: encoded_hash}))


if __name__ == "__main__":
    main()
