"""Journal des appels, cache et consentements de la passerelle LLM.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-06 21:45:16.195999
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_cache",
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("model", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("response_text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "llm_call",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("task", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("model", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_cloud", sa.Boolean(), nullable=False),
        sa.Column("prompt_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("prompt_version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("error", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("llm_call", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_llm_call_created_at"), ["created_at"], unique=False)

    op.create_table(
        "llm_consent",
        sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("granted_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("provider"),
    )


def downgrade() -> None:
    op.drop_table("llm_consent")
    with op.batch_alter_table("llm_call", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_llm_call_created_at"))

    op.drop_table("llm_call")
    op.drop_table("llm_cache")
