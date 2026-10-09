"""add media library"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = ("d4e5f6a7b8c9", "4b77b00f4152")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("advertiser_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Enum("IMAGE", "VIDEO", name="mediakind", native_enum=False), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(64), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Numeric(8, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["advertiser_id"], ["advertisers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("stored_name", name="uq_media_assets_stored_name"),
    )
    op.create_index("ix_media_assets_advertiser_id", "media_assets", ["advertiser_id"])
    op.add_column("creatives", sa.Column("media_asset_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_creatives_media_asset_id", "creatives", ["media_asset_id"])
    op.create_foreign_key(
        "fk_creatives_media_asset", "creatives", "media_assets",
        ["media_asset_id"], ["id"], ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_creatives_media_asset", "creatives", type_="foreignkey")
    op.drop_index("ix_creatives_media_asset_id", table_name="creatives")
    op.drop_column("creatives", "media_asset_id")
    op.drop_table("media_assets")