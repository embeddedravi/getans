"""add payouts table

Revision ID: 9d4e1f2a3b44
Revises: 8c3d0e1f2a33
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9d4e1f2a3b44"
down_revision: Union[str, None] = "8c3d0e1f2a33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payouts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("publisher_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PROCESSING", "PAID", "FAILED", "CANCELLED",
                    name="payoutstatus", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "payment_method",
            sa.Enum("STRIPE", "PAYPAL", "WIRE_TRANSFER", name="paymentmethod", native_enum=False),
            nullable=True,
        ),
        sa.Column("payout_email", sa.String(255), nullable=False),
        sa.Column("reference", sa.String(128), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["publisher_id"], ["publishers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("reference", name="uq_payouts_reference"),
        sa.CheckConstraint("amount > 0.00", name="check_positive_payout_amount"),
        sa.CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="check_valid_payout_period",
        ),
    )
    op.create_index("ix_payouts_publisher_id", "payouts", ["publisher_id"])
    op.create_index("ix_payouts_status", "payouts", ["status"])
    op.create_index("ix_payouts_publisher_status", "payouts", ["publisher_id", "status"])


def downgrade() -> None:
    op.drop_table("payouts")