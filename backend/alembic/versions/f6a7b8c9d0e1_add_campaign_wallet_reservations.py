"""track advertiser campaign reservations and precise spend

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column("reserved_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
    )
    op.create_check_constraint(
        "check_nonnegative_reserved_amount", "campaigns", "reserved_amount >= 0.00"
    )
    op.alter_column(
        "campaigns",
        "spent_amount",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Numeric(12, 6),
        existing_nullable=False,
    )
    op.alter_column("campaigns", "reserved_amount", server_default=None)


def downgrade() -> None:
    op.alter_column(
        "campaigns",
        "spent_amount",
        existing_type=sa.Numeric(12, 6),
        type_=sa.Numeric(12, 2),
        existing_nullable=False,
    )
    op.drop_constraint("check_nonnegative_reserved_amount", "campaigns", type_="check")
    op.drop_column("campaigns", "reserved_amount")
