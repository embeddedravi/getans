"""add user mobile, make email optional

Revision ID: 7b2c9d4e5f10
Revises: 6f7a8f1e1745
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7b2c9d4e5f10"
down_revision: Union[str, None] = "6f7a8f1e1745"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mobile", sa.String(length=15), nullable=True))
    op.create_index(op.f("ix_users_mobile"), "users", ["mobile"], unique=True)
    op.alter_column(
        "users", "email", existing_type=sa.String(length=191), nullable=True
    )
    op.create_check_constraint(
        "check_user_has_contact", "users", "mobile IS NOT NULL OR email IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_constraint("check_user_has_contact", "users", type_="check")
    op.alter_column(
        "users", "email", existing_type=sa.String(length=191), nullable=False
    )
    op.drop_index(op.f("ix_users_mobile"), table_name="users")
    op.drop_column("users", "mobile")