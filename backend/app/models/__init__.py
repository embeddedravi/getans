"""Import every model so SQLAlchemy's mapper registry is fully populated
whenever anything imports from app.models -- avoids NoReferencedTableError /
InvalidRequestError from partially-registered relationships."""

from app.models.ad_unit import AdUnit  # noqa: F401
from app.models.advertiser import Advertiser  # noqa: F401
from app.models.campaign import Campaign  # noqa: F401
from app.models.creative import Creative  # noqa: F401
from app.models.event import Event  # noqa: F401
from app.models.publisher import Publisher  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "AdUnit",
    "Advertiser",
    "Campaign",
    "Creative",
    "Event",
    "Publisher",
    "User",
]