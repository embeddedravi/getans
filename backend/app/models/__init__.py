"""Import every model so SQLAlchemy's mapper registry is fully populated
whenever anything imports from app.models -- avoids NoReferencedTableError /
InvalidRequestError from partially-registered relationships."""

from app.models.ad_unit import AdUnit  # noqa: F401
from app.models.ad_report import AdReport  # noqa: F401
from app.models.advertiser import Advertiser  # noqa: F401
from app.models.campaign import Campaign  # noqa: F401
from app.models.creative import Creative  # noqa: F401
from app.models.event import Event  # noqa: F401
from app.models.media_asset import MediaAsset  # noqa: F401
from app.models.publisher import Publisher  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.payment import AdvertiserTopUp, Payout  # noqa: F401
from app.models.otp import OTPCode  # noqa: F401
from app.models.support_ticket import SupportTicket, SupportTicketMessage  # noqa: F401

__all__ = [
    "AdUnit",
    "AdReport",
    "Advertiser",
    "Campaign",
    "Creative",
    "Event",
    "Publisher",
    "User",
    "Payout",
    "AdvertiserTopUp",
    "OTPCode",
    "SupportTicket",
    "SupportTicketMessage",
]
