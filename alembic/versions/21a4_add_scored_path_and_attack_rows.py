"""add scored_path and attack_rows to prediction_summaries

Revision ID: 9f2b3b1c7d11
Revises: 6c01ce9e5b08
Create Date: 2025-12-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f2b3b1c7d11"
down_revision: Union[str, Sequence[str], None] = "6c01ce9e5b08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("prediction_summaries", sa.Column("attack_rows", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("prediction_summaries", sa.Column("scored_path", sa.String(length=512), nullable=True))

    # optional: уберём server_default после заполнения
    op.alter_column("prediction_summaries", "attack_rows", server_default=None)


def downgrade() -> None:
    op.drop_column("prediction_summaries", "scored_path")
    op.drop_column("prediction_summaries", "attack_rows")
