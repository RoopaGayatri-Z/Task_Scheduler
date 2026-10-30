"""
One-off migration: converts any legacy PLAIN-TEXT passwords in users.password_hash
into salted bcrypt hashes. Safe to run repeatedly (already-hashed rows are skipped).

Usage (from backend/ with the venv active and DATABASE_URL + JWT_SECRET set):
    python migrate_hash_passwords.py
"""
from database import SessionLocal
import models
from auth import hash_password


def looks_like_bcrypt(value: str) -> bool:
    return value.startswith(("$2a$", "$2b$", "$2y$")) and len(value) == 60


def main():
    db = SessionLocal()
    migrated = 0
    for user in db.query(models.User).all():
        if not looks_like_bcrypt(user.password_hash):
            user.password_hash = hash_password(user.password_hash)
            migrated += 1
    db.commit()
    db.close()
    print(f"Migrated {migrated} plain-text password(s) to bcrypt.")


if __name__ == "__main__":
    main()
