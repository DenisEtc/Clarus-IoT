"""seed monthly plan

Revision ID: 92b86a1754dd
Revises: 7018251aabc8
Create Date: 2025-12-13 15:52:33.268906

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid



# revision identifiers, used by Alembic.
revision: str = '92b86a1754dd'
down_revision: Union[str, Sequence[str], None] = '7018251aabc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    plans = sa.table(
        "plans",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("duration_days", sa.Integer),
        sa.column("price_cents", sa.Integer),
        sa.column("currency", sa.String),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(
        plans,
        [
            {
                "id": uuid.uuid4(),
                "code": "MONTHLY_1M",
                "name": "Monthly subscription (1 month)",
                "duration_days": 30,
                "price_cents": 9900,
                "currency": "RUB",
                "is_active": True,
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM plans WHERE code = 'MONTHLY_1M'")