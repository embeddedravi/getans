"""add visitor ad reports and review rounds

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ad_units",
        sa.Column("report_review_round", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("ad_units", "report_review_round", server_default=None)
    op.create_table(
        "ad_reports",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ad_unit_id", sa.BigInteger(), nullable=False),
        sa.Column("creative_id", sa.BigInteger(), nullable=True),
        sa.Column("reporter_hash", sa.String(length=64), nullable=False),
        sa.Column("review_round", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ad_unit_id"], ["ad_units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creative_id"], ["creatives.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("ad_unit_id", "review_round", "reporter_hash", name="uq_ad_reports_visitor_round"),
    )
    op.create_index("ix_ad_reports_ad_unit_id", "ad_reports", ["ad_unit_id"])
    op.create_index("ix_ad_reports_creative_id", "ad_reports", ["creative_id"])


def downgrade() -> None:
    op.drop_index("ix_ad_reports_creative_id", table_name="ad_reports")
    op.drop_index("ix_ad_reports_ad_unit_id", table_name="ad_reports")
    op.drop_table("ad_reports")
    op.drop_column("ad_units", "report_review_round")
