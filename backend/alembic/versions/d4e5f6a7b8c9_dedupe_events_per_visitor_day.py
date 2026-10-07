"""deduplicate impression and click events per visitor per day

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("dedupe_key", sa.String(length=64), nullable=True))
    op.create_index("uq_events_dedupe_key", "events", ["dedupe_key"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_events_dedupe_key", table_name="events")
    op.drop_column("events", "dedupe_key")
