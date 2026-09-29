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
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.phone import normalize_indian_mobile

# ── Parse CLI args ────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Seed a demo admin user into the database.")
parser.add_argument("--mobile",   default="9876543210",   help="Indian mobile number (default: 9876543210)")
parser.add_argument("--email",    default=None,           help="Optional email")
#parser.add_argument("--password", default="demo1234")
parser.add_argument("--password", default=None, help="Omit to generate a random one")
parser.add_argument("--allow-production", action="store_true")
parser.add_argument("--role",     default="admin", choices=["admin", "advertiser", "publisher"])
args = parser.parse_args()
generated = args.password is None
if generated:
    args.password = secrets.token_urlsafe(12)
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

if settings.environment == "production" and not args.allow_production:
    sys.exit("Refusing to seed a demo user in production (use --allow-production).")
# ── Async main ────────────────────────────────────────────────────────────────

async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with Session() as db:
        # Check if the user already exists
        result = await db.execute(select(User).where(User.mobile == args.mobile))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"\n⚠️  User '{args.mobile}' already exists (id={existing.id}, role={existing.role}).")
            print("    Use --email to specify a different address, or delete the existing user first.\n")
            await engine.dispose()
            return

        user = User(
            mobile=args.mobile,
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
