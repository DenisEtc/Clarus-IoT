"""add user role

Revision ID: a71d9ecc5865
Revises: 92b86a1754dd
Create Date: 2025-12-13 16:29:31.577377

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a71d9ecc5865'
down_revision: Union[str, Sequence[str], None] = '92b86a1754dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=16), nullable=False, server_default="user"))
    # после добавления можно убрать дефолт на уровне БД (опционально)
    op.alter_column("users", "role", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "role")

