"""add advertiser Razorpay wallet top-ups

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "advertiser_topups",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("advertiser_id", sa.BigInteger(), nullable=False),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("payment_id", sa.String(64), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.Enum("CREATED", "PAID", name="topupstatus", native_enum=False), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["advertiser_id"], ["advertisers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("order_id", name="uq_advertiser_topups_order_id"),
        sa.UniqueConstraint("payment_id", name="uq_advertiser_topups_payment_id"),
        sa.CheckConstraint("amount >= 1.00", name="check_min_advertiser_topup"),
    )
    op.create_index("ix_advertiser_topups_advertiser_id", "advertiser_topups", ["advertiser_id"])


def downgrade() -> None:
    op.drop_table("advertiser_topups")
