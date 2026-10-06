"""lock advertiser currency to INR

Revision ID: a1b2c3d4e5f6
Revises: 9d4e1f2a3b44
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9d4e1f2a3b44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep the recorded numeric amounts and move every account to the platform currency.
    op.execute("UPDATE advertisers SET currency = 'INR'")
    op.alter_column(
        "advertisers",
        "currency",
        existing_type=sa.Enum("USD", "EUR", "GBP", name="currency", native_enum=False),
        type_=sa.Enum("INR", name="currency", native_enum=False),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "advertisers",
        "currency",
        existing_type=sa.Enum("INR", name="currency", native_enum=False),
        type_=sa.Enum("USD", "EUR", "GBP", name="currency", native_enum=False),
        existing_nullable=False,
    )
    op.execute("UPDATE advertisers SET currency = 'USD'")
