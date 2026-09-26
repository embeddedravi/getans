"""
create_demo_user.py — Run from the backend/ directory to seed a demo admin user.

Usage:
    cd backend
    py create_demo_user.py
    # or with custom credentials:
    py create_demo_user.py --email admin@demo.com --password secret123
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── Parse CLI args ────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Seed a demo admin user into the database.")
parser.add_argument("--email",    default="admin@demo.com", help="User email (default: admin@demo.com)")
parser.add_argument("--password", default="demo1234",       help="User password (default: demo1234)")
parser.add_argument("--role",     default="admin",          choices=["admin", "advertiser", "publisher"],
                    help="User role (default: admin)")
args = parser.parse_args()

# ── Import app modules (must be run from backend/) ────────────────────────────

try:
    from app.config import settings
    from app.core.security import hash_password
    from app.db.base import Base
    from app.models import ad_unit, advertiser, campaign, creative, event, publisher  # noqa: F401
    from app.models.user import User
except ModuleNotFoundError as exc:
    print(f"\n❌  Import error: {exc}")
    print("    Make sure you run this script from the 'backend/' directory.\n")
    sys.exit(1)


# ── Async main ────────────────────────────────────────────────────────────────

async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with Session() as db:
        # Check if the user already exists
        result = await db.execute(select(User).where(User.email == args.email))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"\n⚠️  User '{args.email}' already exists (id={existing.id}, role={existing.role}).")
            print("    Use --email to specify a different address, or delete the existing user first.\n")
            await engine.dispose()
            return

        user = User(
            email=args.email,
            hashed_password=hash_password(args.password),
            role=args.role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    await engine.dispose()

    print()
    print("✅  Demo user created successfully!")
    print(f"    Email    : {user.email}")
    print(f"    Password : {args.password}")
    print(f"    Role     : {user.role}")
    print(f"    ID       : {user.id}")
    print()
    print("    → Log in at http://127.0.0.1:5000/login")
    print()


if __name__ == "__main__":
    asyncio.run(main())
