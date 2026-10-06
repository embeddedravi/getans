"""Add approval statuses and rejection reasons.

Revision ID: 4b77b00f4152
Revises: 9d4e1f2a3b44
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4b77b00f4152"
down_revision: Union[str, None] = "9d4e1f2a3b44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep this migration limited to approval fields. The generated version
    # also dropped OTP storage and changed unrelated foreign keys.
    op.add_column(
        "ad_units",
        sa.Column(
            "status",
            sa.Enum("PENDING_REVIEW", "APPROVED", "REJECTED", name="adunitstatus", native_enum=False),
            nullable=False,
            server_default="PENDING_REVIEW",
        ),
    )
    op.add_column("ad_units", sa.Column("rejection_reason", sa.String(length=500), nullable=True))
    op.create_index(op.f("ix_ad_units_status"), "ad_units", ["status"], unique=False)
    op.add_column("advertisers", sa.Column("rejection_reason", sa.String(length=500), nullable=True))
    op.add_column("publishers", sa.Column("rejection_reason", sa.String(length=500), nullable=True))
    op.alter_column("ad_units", "status", server_default=None)


def downgrade() -> None:
    op.drop_column("publishers", "rejection_reason")
    op.drop_column("advertisers", "rejection_reason")
    op.drop_index(op.f("ix_ad_units_status"), table_name="ad_units")
    op.drop_column("ad_units", "rejection_reason")
    op.drop_column("ad_units", "status")
