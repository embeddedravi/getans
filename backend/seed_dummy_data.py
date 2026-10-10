"""
seed_dummy_data.py - fill every table with dummy rows so you can test lists and pagers.

Put this file in backend/ (next to create_demo_user.py) and run from there:

    cd backend
    python seed_dummy_data.py                      # default volume
    python seed_dummy_data.py --reset              # delete earlier dummy data, then re-seed
    python seed_dummy_data.py --advertisers 60 --campaigns-per-advertiser 6 --events 20000

Everything it creates is tagged so --reset can remove it without touching real data:
    * publishers / advertisers are named "Demo Publisher N" / "Demo Advertiser N"
    * users have mobiles in the range +917000000000 - +917009999999
All dummy users share one password (printed at the end). Never run this against production.

Default volume (chosen so the 50-row API page size is exceeded in most lists):
    30 publishers, ~150 ad units, 30 advertisers, 150 campaigns, ~300 creatives,
    ~90 media assets, 5000 events, 60 payouts, 60 top-ups, ~100 ad reports, ~70 users.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import secrets
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

parser = argparse.ArgumentParser(description="Seed dummy data into every table.")
parser.add_argument("--publishers", type=int, default=30)
parser.add_argument("--ad-units-per-publisher", type=int, default=5)
parser.add_argument("--advertisers", type=int, default=30)
parser.add_argument("--campaigns-per-advertiser", type=int, default=5)
parser.add_argument("--media-per-advertiser", type=int, default=3)
parser.add_argument("--events", type=int, default=5000)
parser.add_argument("--payouts", type=int, default=60)
parser.add_argument("--topups", type=int, default=60)
parser.add_argument("--reports", type=int, default=100)
parser.add_argument("--password", default="DemoPass123!", help="Password for all dummy users")
parser.add_argument("--seed", type=int, default=42, help="Random seed (repeatable data)")
parser.add_argument("--reset", action="store_true", help="Delete previous dummy data first")
parser.add_argument("--allow-production", action="store_true")
args = parser.parse_args()

try:
    from sqlalchemy import delete, func, insert, select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import settings
    from app.core.security import hash_password
    from app.models.ad_report import AdReport
    from app.models.ad_unit import AdFormatType, AdUnit, AdUnitStatus
    from app.models.advertiser import AccountStatus, Advertiser, Currency
    from app.models.campaign import BiddingStrategy, Campaign, CampaignStatus
    from app.models.creative import Creative, CreativeFormat, ReviewStatus
    from app.models.event import Event, EventType
    from app.models.media_asset import MediaAsset, MediaKind
    from app.models.otp import OTPCode
    from app.models.payment import AdvertiserTopUp, Payout, PayoutStatus, TopUpStatus
    from app.models.publisher import PaymentMethod, Publisher, PublisherStatus
    from app.models.user import User, UserRole
except ModuleNotFoundError as exc:
    print(f"\nImport error: {exc}")
    print("Run this script from the 'backend/' directory with your venv active.\n")
    sys.exit(1)

if settings.environment == "production" and not args.allow_production:
    sys.exit("Refusing to seed dummy data in production (use --allow-production if you really mean it).")

random.seed(args.seed)
NOW = datetime.now(timezone.utc)

# --------------------------------------------------------------------------- data pools

SIZES = [(300, 250), (728, 90), (160, 600), (320, 50), (300, 600)]
CATEGORIES = ["News", "Tech", "Sports", "Finance", "Travel", "Food", "Health", "Gaming", "Education"]
INDUSTRIES = ["Retail", "Finance", "Automotive", "Telecom", "FMCG", "Travel", "Education", "Real estate"]
COUNTRIES = ["IN", "IN", "IN", "IN", "US", "GB", "AE", "SG", "CA", "AU"]
REPORT_REASONS = ["misleading", "adult_content", "inappropriate", "scam", "other"]
COLORS = ["#d9534f", "#5b8def", "#f2a93b", "#5cb85c", "#8e44ad", "#16a085"]
COST = {
    EventType.IMPRESSION: Decimal("0.001000"),
    EventType.CLICK: Decimal("0.100000"),
    EventType.CONVERSION: Decimal("1.000000"),
}


def wchoice(options, weights):
    return random.choices(options, weights=weights, k=1)[0]


def money(low: float, high: float, places: int = 2) -> Decimal:
    return Decimal(str(round(random.uniform(low, high), places)))


def rand_dt(days_back: int) -> datetime:
    return NOW - timedelta(seconds=random.randint(0, days_back * 86400))


_mobile_counter = 0


def next_mobile() -> str:
    """Unique, valid-looking Indian mobiles in the +917000000000 range."""
    global _mobile_counter
    _mobile_counter += 1
    return f"+91{7000000000 + _mobile_counter}"


def write_placeholder_png(path: Path, w: int, h: int) -> bool:
    """Write a real image so media thumbnails render. Needs Pillow; skipped if missing."""
    try:
        from PIL import Image
    except ImportError:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (w, h), random.choice(COLORS)).save(path, "PNG")
    return True


# --------------------------------------------------------------------------- reset

async def reset_dummy(db: AsyncSession) -> None:
    pub_ids = select(Publisher.id).where(Publisher.name.like("Demo Publisher %"))
    adv_ids = select(Advertiser.id).where(Advertiser.name.like("Demo Advertiser %"))
    unit_ids = select(AdUnit.id).where(AdUnit.publisher_id.in_(pub_ids))
    camp_ids = select(Campaign.id).where(Campaign.advertiser_id.in_(adv_ids))

    media_names = (
        await db.execute(select(MediaAsset.stored_name).where(MediaAsset.advertiser_id.in_(adv_ids)))
    ).scalars().all()

    await db.execute(delete(AdReport).where(AdReport.ad_unit_id.in_(unit_ids)))
    await db.execute(delete(Event).where(Event.campaign_id.in_(camp_ids)))
    await db.execute(delete(Payout).where(Payout.publisher_id.in_(pub_ids)))
    await db.execute(delete(AdvertiserTopUp).where(AdvertiserTopUp.advertiser_id.in_(adv_ids)))
    await db.execute(delete(Creative).where(Creative.campaign_id.in_(camp_ids)))
    await db.execute(delete(MediaAsset).where(MediaAsset.advertiser_id.in_(adv_ids)))
    await db.execute(delete(Campaign).where(Campaign.advertiser_id.in_(adv_ids)))
    await db.execute(delete(AdUnit).where(AdUnit.publisher_id.in_(pub_ids)))
    await db.execute(delete(OTPCode).where(OTPCode.mobile.like("+91700%")))
    await db.execute(delete(User).where(User.mobile.like("+91700%")))
    await db.execute(delete(Advertiser).where(Advertiser.name.like("Demo Advertiser %")))
    await db.execute(delete(Publisher).where(Publisher.name.like("Demo Publisher %")))
    await db.commit()

    for name in media_names:
        (settings.media_dir / name).unlink(missing_ok=True)
    print("Removed previous dummy data.")


# --------------------------------------------------------------------------- seeding

async def seed(db: AsyncSession) -> dict[str, int]:
    counts: dict[str, int] = {}
    pw_hash = hash_password(args.password)  # bcrypt is slow: hash once, reuse for every user

    # ---- publishers -------------------------------------------------------------
    publishers: list[Publisher] = []
    for i in range(1, args.publishers + 1):
        status = wchoice(
            [PublisherStatus.ACTIVE, PublisherStatus.PENDING_APPROVAL, PublisherStatus.SUSPENDED, PublisherStatus.REJECTED],
            [70, 15, 8, 7],
        )
        publishers.append(
            Publisher(
                name=f"Demo Publisher {i}",
                site_url=f"https://publisher{i}.example.com",
                domain=f"publisher{i}.example.com",
                category=random.choice(CATEGORIES),
                status=status,
                is_active=status == PublisherStatus.ACTIVE,
                ads_txt_verified=random.random() < 0.6,
                revenue_share_percentage=Decimal(random.choice(["60.00", "65.00", "70.00", "75.00"])),
                unpaid_earnings=money(500, 50000),
                payout_email=f"payouts{i}@publisher{i}.example.com",
                payment_method=random.choice([None, *PaymentMethod]),
                rejection_reason="Site content does not meet policy" if status == PublisherStatus.REJECTED else None,
            )
        )
    db.add_all(publishers)
    await db.flush()
    counts["publishers"] = len(publishers)

    # ---- ad units ---------------------------------------------------------------
    ad_units: list[AdUnit] = []
    for pub in publishers:
        for n in range(1, args.ad_units_per_publisher + 1):
            w, h = random.choice(SIZES)
            status = wchoice([AdUnitStatus.APPROVED, AdUnitStatus.PENDING_REVIEW, AdUnitStatus.REJECTED], [70, 20, 10])
            ad_units.append(
                AdUnit(
                    publisher_id=pub.id,
                    slot_name=f"slot-{n}-{w}x{h}",
                    description=f"Placement {n} on {pub.name}",
                    format_type=wchoice(list(AdFormatType), [50, 25, 10, 10, 5]),
                    width=w,
                    height=h,
                    reserve_price=money(0, 2, 4),
                    is_active=status == AdUnitStatus.APPROVED and random.random() < 0.9,
                    allow_house_ads=random.random() < 0.8,
                    status=status,
                    rejection_reason="Placement is too intrusive" if status == AdUnitStatus.REJECTED else None,
                    report_review_round=random.randint(0, 2),
                )
            )
    db.add_all(ad_units)
    await db.flush()
    counts["ad_units"] = len(ad_units)

    # ---- advertisers ------------------------------------------------------------
    advertisers: list[Advertiser] = []
    for i in range(1, args.advertisers + 1):
        status = wchoice(
            [AccountStatus.ACTIVE, AccountStatus.PENDING_VERIFICATION, AccountStatus.SUSPENDED,
             AccountStatus.REJECTED, AccountStatus.ARCHIVED],
            [65, 15, 8, 7, 5],
        )
        advertisers.append(
            Advertiser(
                name=f"Demo Advertiser {i}",
                company_legal_name=f"Demo Advertiser {i} Pvt Ltd",
                website_url=f"https://advertiser{i}.example.com",
                industry=random.choice(INDUSTRIES),
                status=status,
                is_verified=status == AccountStatus.ACTIVE,
                billing_email=f"billing{i}@advertiser{i}.example.com",
                phone_number=f"+9170{random.randint(10000000, 99999999)}",
                currency=Currency.INR,
                balance=money(0, 100000),
                credit_limit=money(0, 20000),
                notes="Dummy advertiser for pager testing" if i % 5 == 0 else None,
                rejection_reason="Documents could not be verified" if status == AccountStatus.REJECTED else None,
            )
        )
    db.add_all(advertisers)
    await db.flush()
    counts["advertisers"] = len(advertisers)

    # ---- users + otp codes ------------------------------------------------------
    users: list[User] = []

    def add_user(role: UserRole, label: str, *, publisher_id=None, advertiser_id=None) -> None:
        mobile = next_mobile()
        users.append(
            User(
                mobile=mobile,
                email=f"{label}@demo.example.com",
                hashed_password=pw_hash,
                first_name=label.split(".")[0].title(),
                last_name="Demo",
                role=role,
                publisher_id=publisher_id,
                advertiser_id=advertiser_id,
                is_active=random.random() < 0.92,
                is_verified=random.random() < 0.75,
                last_login_at=rand_dt(30) if random.random() < 0.7 else None,
            )
        )

    for n in range(1, 3):
        add_user(UserRole.ADMIN, f"admin.{n}")
    for n in range(1, 4):
        add_user(UserRole.STAFF, f"staff.{n}")
    for pub in publishers:
        add_user(UserRole.PUBLISHER, f"publisher.{pub.id}", publisher_id=pub.id)
    for adv in advertisers:
        add_user(UserRole.ADVERTISER, f"advertiser.{adv.id}", advertiser_id=adv.id)
    db.add_all(users)
    await db.flush()
    counts["users"] = len(users)

    otps: list[OTPCode] = []
    for user in random.sample(users, k=min(len(users), 40)):
        for _ in range(random.randint(1, 3)):
            consumed = random.random() < 0.5
            created = rand_dt(2)
            otps.append(
                OTPCode(
                    mobile=user.mobile,
                    code_hash=secrets.token_hex(32),  # 64 hex chars, matches String(64)
                    expires_at=created + timedelta(minutes=5),
                    attempts=random.randint(0, 5),
                    consumed_at=created + timedelta(seconds=30) if consumed else None,
                )
            )
    db.add_all(otps)
    counts["otp_codes"] = len(otps)

    # ---- media assets (real PNG files when Pillow is installed) ----------------
    media_by_adv: dict[int, list[MediaAsset]] = {}
    media_total = 0
    for adv in advertisers:
        items: list[MediaAsset] = []
        for n in range(args.media_per_advertiser):
            w, h = random.choice(SIZES)
            is_video = random.random() < 0.2
            ext = ".mp4" if is_video else ".png"
            stored = secrets.token_hex(16) + ext
            size_bytes = random.randint(200_000, 40_000_000) if is_video else random.randint(5_000, 4_000_000)
            if not is_video:
                if write_placeholder_png(settings.media_dir / stored, w, h):
                    size_bytes = (settings.media_dir / stored).stat().st_size
            items.append(
                MediaAsset(
                    advertiser_id=adv.id,
                    kind=MediaKind.VIDEO if is_video else MediaKind.IMAGE,
                    original_filename=f"asset-{adv.id}-{n + 1}{ext}",
                    stored_name=stored,
                    content_type="video/mp4" if is_video else "image/png",
                    size_bytes=size_bytes,
                    width=w,
                    height=h,
                    duration_seconds=money(3, 30) if is_video else None,
                )
            )
        db.add_all(items)
        media_by_adv[adv.id] = items
        media_total += len(items)
    await db.flush()
    counts["media_assets"] = media_total

    # ---- campaigns --------------------------------------------------------------
    campaigns: list[Campaign] = []
    for adv in advertisers:
        for n in range(1, args.campaigns_per_advertiser + 1):
            status = wchoice(
                [CampaignStatus.ACTIVE, CampaignStatus.DRAFT, CampaignStatus.SCHEDULED, CampaignStatus.PAUSED,
                 CampaignStatus.COMPLETED, CampaignStatus.EXHAUSTED, CampaignStatus.ARCHIVED],
                [40, 15, 10, 10, 10, 8, 7],
            )
            start = NOW - timedelta(days=random.randint(-20, 90))
            end = start + timedelta(days=random.randint(10, 90)) if random.random() < 0.8 else None
            total_budget = money(5000, 200000) if random.random() < 0.7 else None
            targeting = None
            if random.random() < 0.5:
                targeting = {
                    "countries": random.sample(["IN", "US", "GB", "AE", "SG"], k=random.randint(1, 3)),
                    "device_types": random.sample(["mobile", "desktop"], k=random.randint(1, 2)),
                    "keywords": random.sample(["news", "tech", "sports", "finance", "travel"], k=random.randint(1, 3)),
                }
            campaigns.append(
                Campaign(
                    advertiser_id=adv.id,
                    name=f"Campaign {n} - {adv.name}",
                    status=status,
                    is_active=status in (CampaignStatus.ACTIVE, CampaignStatus.SCHEDULED) and random.random() < 0.9,
                    priority=random.randint(1, 100),
                    start_date=start,
                    end_date=end,
                    bidding_strategy=random.choice(list(BiddingStrategy)),
                    bid_amount=money(0.05, 5, 4),
                    daily_cap=money(100, 5000) if random.random() < 0.6 else None,
                    total_budget=total_budget,
                    spent_amount=money(0, float(total_budget) * 0.8) if total_budget else money(0, 3000),
                    targeting_rules=targeting,
                )
            )
    db.add_all(campaigns)
    await db.flush()
    counts["campaigns"] = len(campaigns)

    # ---- creatives --------------------------------------------------------------
    creatives: list[Creative] = []
    adv_by_id = {a.id: a for a in advertisers}
    for camp in campaigns:
        for n in range(1, random.randint(1, 3) + 1):
            media = None
            if random.random() < 0.5 and media_by_adv.get(camp.advertiser_id):
                media = random.choice(media_by_adv[camp.advertiser_id])
            if media is not None:
                w, h = media.width, media.height
                asset_url = media.url
                fmt = CreativeFormat.VIDEO if media.kind == MediaKind.VIDEO else CreativeFormat.IMAGE
            else:
                w, h = random.choice(SIZES)
                asset_url = f"https://placehold.co/{w}x{h}/png?text=Demo+Ad"
                fmt = CreativeFormat.IMAGE
            review = wchoice([ReviewStatus.APPROVED, ReviewStatus.PENDING, ReviewStatus.REJECTED], [60, 28, 12])
            creatives.append(
                Creative(
                    campaign_id=camp.id,
                    media_asset_id=media.id if media is not None else None,
                    name=f"Creative {n} ({w}x{h})",
                    asset_url=asset_url,
                    click_url=f"https://{adv_by_id[camp.advertiser_id].website_url.split('//')[1]}/landing/{camp.id}",
                    format=fmt,
                    width=w,
                    height=h,
                    is_active=random.random() < 0.9,
                    review_status=review,
                    rejection_reason="Image is blurry or low quality" if review == ReviewStatus.REJECTED else None,
                    weight=random.choice([50, 100, 100, 200]),
                )
            )
    db.add_all(creatives)
    await db.flush()
    counts["creatives"] = len(creatives)

    # ---- events (bulk insert in batches) ---------------------------------------
    if creatives and ad_units:
        creative_pairs = [(c.id, c.campaign_id) for c in creatives]
        unit_ids = [u.id for u in ad_units]
        types = [EventType.IMPRESSION, EventType.CLICK, EventType.CONVERSION]
        batch: list[dict] = []
        for _ in range(args.events):
            creative_id, campaign_id = random.choice(creative_pairs)
            etype = wchoice(types, [92, 7, 1])
            batch.append(
                {
                    "event_id": str(uuid.uuid4()),
                    "dedupe_key": None,
                    "ad_unit_id": random.choice(unit_ids),
                    "campaign_id": campaign_id,
                    "creative_id": creative_id,
                    "type": etype,
                    "timestamp": rand_dt(30),
                    "cost": COST[etype],
                    "is_valid": random.random() < 0.97,
                    "user_ip": f"203.0.113.{random.randint(1, 254)}",
                    "user_agent": random.choice(["Mozilla/5.0 (Windows NT 10.0)", "Mozilla/5.0 (Android 14; Mobile)",
                                                 "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)"]),
                    "country_code": random.choice(COUNTRIES),
                    "meta": None,
                }
            )
            if len(batch) >= 1000:
                await db.execute(insert(Event), batch)
                batch = []
        if batch:
            await db.execute(insert(Event), batch)
    counts["events"] = args.events

    # ---- ad reports (unique per ad_unit + round + reporter) ---------------------
    reports: list[AdReport] = []
    seen: set[tuple[int, int, str]] = set()
    attempts = 0
    while len(reports) < args.reports and attempts < args.reports * 5 and creatives:
        attempts += 1
        unit = random.choice(ad_units)
        creative = random.choice(creatives)
        reporter = secrets.token_hex(32)
        key = (unit.id, unit.report_review_round, reporter)
        if key in seen:
            continue
        seen.add(key)
        reports.append(
            AdReport(
                ad_unit_id=unit.id,
                creative_id=creative.id,
                reporter_hash=reporter,
                review_round=unit.report_review_round,
                reason=random.choice(REPORT_REASONS),
                created_at=rand_dt(14),
            )
        )
    db.add_all(reports)
    counts["ad_reports"] = len(reports)

    # ---- advertiser top-ups -----------------------------------------------------
    topups: list[AdvertiserTopUp] = []
    for i in range(args.topups):
        adv = random.choice(advertisers)
        paid = random.random() < 0.75
        created = rand_dt(60)
        topups.append(
            AdvertiserTopUp(
                advertiser_id=adv.id,
                order_id=f"order_demo_{i:05d}_{secrets.token_hex(4)}",
                payment_id=f"pay_demo_{i:05d}_{secrets.token_hex(4)}" if paid else None,
                amount=Decimal(random.choice([500, 1000, 2500, 5000, 10000, 25000])).quantize(Decimal("0.01")),
                status=TopUpStatus.PAID if paid else TopUpStatus.CREATED,
                paid_at=created + timedelta(minutes=2) if paid else None,
                created_at=created,
            )
        )
    db.add_all(topups)
    counts["advertiser_topups"] = len(topups)

    # ---- payouts ----------------------------------------------------------------
    payouts: list[Payout] = []
    for i in range(args.payouts):
        pub = random.choice(publishers)
        status = wchoice(
            [PayoutStatus.PENDING, PayoutStatus.PROCESSING, PayoutStatus.PAID, PayoutStatus.FAILED, PayoutStatus.CANCELLED],
            [20, 10, 45, 10, 15],
        )
        period_end = rand_dt(60)
        period_start = period_end - timedelta(days=30)
        payouts.append(
            Payout(
                publisher_id=pub.id,
                amount=money(100, 8000),
                status=status,
                payment_method=random.choice(list(PaymentMethod)),
                payout_email=pub.payout_email,
                reference=f"DEMO-TXN-{i:05d}-{secrets.token_hex(3)}" if status == PayoutStatus.PAID else None,
                failure_reason="Bank rejected the transfer" if status == PayoutStatus.FAILED else None,
                notes="Dummy payout" if i % 7 == 0 else None,
                period_start=period_start,
                period_end=period_end,
                paid_at=period_end + timedelta(days=2) if status == PayoutStatus.PAID else None,
                created_at=period_end + timedelta(days=1),
            )
        )
    db.add_all(payouts)
    counts["payouts"] = len(payouts)

    await db.commit()
    return counts


# --------------------------------------------------------------------------- main

async def main() -> None:
    engine = create_async_engine(settings.database_url.get_secret_value(), echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with Session() as db:
        existing = await db.scalar(
            select(func.count()).select_from(Publisher).where(Publisher.name.like("Demo Publisher %"))
        )
        if existing and not args.reset:
            await engine.dispose()
            sys.exit(f"Found {existing} dummy publishers already. Re-run with --reset to replace them.")
        if args.reset:
            await reset_dummy(db)

        counts = await seed(db)

    await engine.dispose()

    print("\nDummy data created:")
    for table, n in counts.items():
        print(f"  {table:<20} {n:>7}")
    print(f"\nAll dummy users share the password: {args.password}")
    print("Mobiles run from +917000000001 upward. The first two are admins, the next three are staff,")
    print("then one user per publisher, then one per advertiser.")
    print("Tip: log in as the first admin (+917000000001) to browse every list.\n")


if __name__ == "__main__":
    asyncio.run(main())
