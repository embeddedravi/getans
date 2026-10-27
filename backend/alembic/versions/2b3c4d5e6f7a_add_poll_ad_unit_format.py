"""add poll ad unit format

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b3c4d5e6f7a"
down_revision: Union[str, None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # AdFormatType uses SQLAlchemy's non-native Enum, which stores member names.
    op.alter_column(
        "ad_units",
        "format_type",
        existing_type=sa.Enum(
            "DISPLAY", "BANNER", "NATIVE", "VIDEO", "INTERSTITIAL",
            name="adformattype", native_enum=False,
        ),
        type_=sa.Enum(
            "DISPLAY", "BANNER", "NATIVE", "VIDEO", "INTERSTITIAL", "POLL",
            name="adformattype", native_enum=False,
        ),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Existing poll slots cannot be represented by the older enum.
    op.execute("UPDATE ad_units SET format_type = 'DISPLAY' WHERE format_type = 'POLL'")
    op.alter_column(
        "ad_units",
        "format_type",
        existing_type=sa.Enum(
            "DISPLAY", "BANNER", "NATIVE", "VIDEO", "INTERSTITIAL", "POLL",
            name="adformattype", native_enum=False,
        ),
        type_=sa.Enum(
            "DISPLAY", "BANNER", "NATIVE", "VIDEO", "INTERSTITIAL",
            name="adformattype", native_enum=False,
        ),
        existing_nullable=False,
    )
