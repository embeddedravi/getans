"""add otp_codes table

Revision ID: 8c3d0e1f2a33
Revises: 7b2c9d4e5f10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8c3d0e1f2a33"
down_revision: Union[str, None] = "7b2c9d4e5f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("mobile", sa.String(length=15), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_otp_codes_mobile"), "otp_codes", ["mobile"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_otp_codes_mobile"), table_name="otp_codes")
    op.drop_table("otp_codes")
