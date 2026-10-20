"""Merge migration branches and retain sub-rupee ledger precision.

Revision ID: 0c1d2e3f4a5b
Revises: f6a7b8c9d0e1, a1b2c3d4e5f6
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0c1d2e3f4a5b"
down_revision: Union[str, Sequence[str], None] = ("f6a7b8c9d0e1", "a1b2c3d4e5f6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "advertisers", "balance",
        existing_type=sa.Numeric(precision=12, scale=2),
        type_=sa.Numeric(precision=14, scale=6),
        existing_nullable=False,
    )
    op.alter_column(
        "publishers", "unpaid_earnings",
        existing_type=sa.Numeric(precision=12, scale=2),
        type_=sa.Numeric(precision=14, scale=6),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "publishers", "unpaid_earnings",
        existing_type=sa.Numeric(precision=14, scale=6),
        type_=sa.Numeric(precision=12, scale=2),
        existing_nullable=False,
    )
    op.alter_column(
        "advertisers", "balance",
        existing_type=sa.Numeric(precision=14, scale=6),
        type_=sa.Numeric(precision=12, scale=2),
        existing_nullable=False,
    )
