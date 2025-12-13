"""seed demo users v2

Revision ID: 6c01ce9e5b08
Revises: a71d9ecc5865
Create Date: 2025-12-13 16:39:49.744739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import uuid

# revision identifiers, used by Alembic.
revision: str = '6c01ce9e5b08'
down_revision: Union[str, Sequence[str], None] = 'a71d9ecc5865'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



# bcrypt hash для пароля "demo1234"
# (заранее сгенерированный, чтобы миграция не зависела от passlib/bcrypt)
DEMO_PASSWORD_HASH = "$2b$12$C8vYf4v0e9Kj0H2o8g8p1eZ4yW1jvQe9b2u2QnR4m8r2qvJwAqVvW"


def upgrade() -> None:
    conn = op.get_bind()

    demo_user_email = "demo_user@clarus.local"
    demo_admin_email = "demo_admin@clarus.local"

    existing = conn.execute(
        sa.text("SELECT email FROM users WHERE email IN (:u, :a)"),
        {"u": demo_user_email, "a": demo_admin_email},
    ).fetchall()
    existing_emails = {row[0] for row in existing}

    users = sa.table(
        "users",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("role", sa.String),
        sa.column("is_active", sa.Boolean),
    )

    rows = []
    if demo_user_email not in existing_emails:
        rows.append(
            {
                "id": uuid.uuid4(),
                "email": demo_user_email,
                "password_hash": DEMO_PASSWORD_HASH,
                "role": "user",
                "is_active": True,
            }
        )

    if demo_admin_email not in existing_emails:
        rows.append(
            {
                "id": uuid.uuid4(),
                "email": demo_admin_email,
                "password_hash": DEMO_PASSWORD_HASH,
                "role": "admin",
                "is_active": True,
            }
        )

    if rows:
        op.bulk_insert(users, rows)


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE email IN ('demo_user@clarus.local', 'demo_admin@clarus.local')")
